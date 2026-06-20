"""Multi-tenant client entitlements: maps an inbound API key to the models
that client is allowed to SEE and INVOKE.

Additive SaaS layer. It sits BESIDE :mod:`src.core.key_manager` (which holds
upstream PROVIDER keys, a different concern) and shares the same SQLite file.

Design split (resource labels vs subject grants):
  * model -> tier  lives in ``models_schema.json`` (static, version-controlled).
  * client -> entitlement lives here in the ``clients`` table (mutable, secret).

The request path never sees plaintext client keys at rest: only the SHA-256
hash is stored, and resolution compares hashes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import aiosqlite

from src.core.config_loader import get_config


def hash_key(plain_key: str) -> str:
    """Return the SHA-256 hex digest of a client bearer key."""
    return hashlib.sha256(plain_key.encode("utf-8")).hexdigest()


# Daily quota defaults per plan. 0 == unlimited. A client row may override these.
PLAN_DEFAULTS: dict[str, dict[str, int]] = {
    "free": {"requests": 200, "tokens": 100_000},
    "pro": {"requests": 5_000, "tokens": 5_000_000},
    "enterprise": {"requests": 0, "tokens": 0},  # unlimited
    "owner": {"requests": 0, "tokens": 0},  # unlimited
}


def quota_for(plan: str, override: dict[str, int] | None = None) -> dict[str, int]:
    """Resolve a plan's daily quota, applying any per-client override (>0 wins)."""
    base = PLAN_DEFAULTS.get(plan, PLAN_DEFAULTS["free"])
    if not override:
        return dict(base)
    return {
        "requests": override.get("requests") or base["requests"],
        "tokens": override.get("tokens") or base["tokens"],
    }


@dataclass(frozen=True)
class Principal:
    """Resolved identity of the caller behind an API key."""

    client_id: str
    plan: str  # "free" | "pro" | "enterprise" | "owner"
    allowed_tiers: frozenset[str]  # e.g. {"auto"} or {"auto", "dedicated"}
    allowed_model_ids: frozenset[str] = field(default_factory=frozenset)
    is_owner: bool = False  # legacy single-key / admin: sees everything
    quota_requests: int = 0  # daily account cap; 0 == unlimited
    quota_tokens: int = 0  # daily account cap; 0 == unlimited
    model_limits: dict[str, dict[str, int]] = field(default_factory=dict)

    def can_see(self, model) -> bool:
        """True if this principal may see/invoke the given ModelInfo."""
        if self.is_owner:
            return True
        if model.tier in self.allowed_tiers:
            return True
        return model.id in self.allowed_model_ids  # explicit dedicated allocation

    def limit_for(self, model_id: str) -> dict[str, int]:
        """Return the daily {requests, tokens} cap a model is measured against.

        Per-model cap if declared, else the account-level quota (so every bar in
        the UI has a meaningful denominator).
        """
        if model_id in self.model_limits:
            return {
                "requests": self.model_limits[model_id].get("requests", 0),
                "tokens": self.model_limits[model_id].get("tokens", 0),
            }
        return {"requests": self.quota_requests, "tokens": self.quota_tokens}


# Owner principal = today's behavior (sees everything). Used when multi-tenant
# is off, or for the configured shared owner key in multi-tenant mode.
OWNER = Principal(
    client_id="owner",
    plan="owner",
    allowed_tiers=frozenset({"auto", "dedicated"}),
    is_owner=True,
)


class TenantStore:
    """SQLite-backed client directory. Reuses the KeyManager database file."""

    def __init__(self) -> None:
        self._db_path: Path | None = None

    async def init(self) -> None:
        """Create the clients table if it does not exist."""
        self._db_path = Path(get_config().database.path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id              TEXT PRIMARY KEY,
                    api_key_hash    TEXT NOT NULL UNIQUE,
                    plan            TEXT NOT NULL DEFAULT 'free',
                    allowed_tiers   TEXT NOT NULL DEFAULT '["auto"]',
                    allowed_models  TEXT NOT NULL DEFAULT '[]',
                    enabled         INTEGER NOT NULL DEFAULT 1,
                    quota_requests  INTEGER NOT NULL DEFAULT 0,
                    quota_tokens    INTEGER NOT NULL DEFAULT 0,
                    model_limits    TEXT NOT NULL DEFAULT '{}',
                    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_clients_hash ON clients(api_key_hash)"
            )
            # Migrate older databases that predate the quota columns.
            for column, ddl in (
                ("quota_requests", "INTEGER NOT NULL DEFAULT 0"),
                ("quota_tokens", "INTEGER NOT NULL DEFAULT 0"),
                ("model_limits", "TEXT NOT NULL DEFAULT '{}'"),
            ):
                try:
                    await db.execute(f"ALTER TABLE clients ADD COLUMN {column} {ddl}")
                except aiosqlite.OperationalError:
                    pass  # column already exists
            await db.commit()

    async def resolve(self, plain_key: str) -> Principal | None:
        """Return the Principal for a presented key, or None if unknown/disabled."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT id, plan, allowed_tiers, allowed_models, enabled, "
                "quota_requests, quota_tokens, model_limits "
                "FROM clients WHERE api_key_hash = ?",
                (hash_key(plain_key),),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None or not row[4]:
            return None
        plan = row[1]
        quota = quota_for(plan, {"requests": row[5], "tokens": row[6]})
        return Principal(
            client_id=row[0],
            plan=plan,
            allowed_tiers=frozenset(json.loads(row[2])),
            allowed_model_ids=frozenset(json.loads(row[3])),
            quota_requests=quota["requests"],
            quota_tokens=quota["tokens"],
            model_limits=json.loads(row[7]),
        )

    async def upsert_client(
        self,
        client_id: str,
        plain_key: str,
        plan: str = "free",
        allowed_tiers: list[str] | None = None,
        allowed_models: list[str] | None = None,
        enabled: bool = True,
        quota_requests: int = 0,
        quota_tokens: int = 0,
        model_limits: dict[str, dict[str, int]] | None = None,
    ) -> None:
        """Provision or update a client. Call from the admin API or a CLI script.

        ``quota_*`` of 0 inherit the plan default; per-model ``model_limits``
        override the account quota for a specific model.
        """
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO clients
                    (id, api_key_hash, plan, allowed_tiers, allowed_models, enabled,
                     quota_requests, quota_tokens, model_limits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    api_key_hash=excluded.api_key_hash,
                    plan=excluded.plan,
                    allowed_tiers=excluded.allowed_tiers,
                    allowed_models=excluded.allowed_models,
                    enabled=excluded.enabled,
                    quota_requests=excluded.quota_requests,
                    quota_tokens=excluded.quota_tokens,
                    model_limits=excluded.model_limits
                """,
                (
                    client_id,
                    hash_key(plain_key),
                    plan,
                    json.dumps(allowed_tiers or ["auto"]),
                    json.dumps(allowed_models or []),
                    1 if enabled else 0,
                    quota_requests,
                    quota_tokens,
                    json.dumps(model_limits or {}),
                ),
            )
            await db.commit()

    async def list_principals(self) -> list[Principal]:
        """Return a Principal for every enabled client (no keys exposed)."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT id, plan, allowed_tiers, allowed_models, "
                "quota_requests, quota_tokens, model_limits "
                "FROM clients WHERE enabled = 1 ORDER BY id"
            ) as cursor:
                rows = await cursor.fetchall()
        principals: list[Principal] = []
        for row in rows:
            quota = quota_for(row[1], {"requests": row[4], "tokens": row[5]})
            principals.append(
                Principal(
                    client_id=row[0],
                    plan=row[1],
                    allowed_tiers=frozenset(json.loads(row[2])),
                    allowed_model_ids=frozenset(json.loads(row[3])),
                    quota_requests=quota["requests"],
                    quota_tokens=quota["tokens"],
                    model_limits=json.loads(row[6]),
                )
            )
        return principals

    async def delete_client(self, client_id: str) -> None:
        """Remove a client from the directory."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            await db.commit()


# Module-level singleton.
_store: TenantStore | None = None


async def init() -> None:
    """Initialise the module-level tenant store."""
    global _store
    if _store is None:
        _store = TenantStore()
    await _store.init()


async def resolve_principal(plain_key: str) -> Principal | None:
    if _store is None:
        raise RuntimeError("Tenant store has not been initialised")
    return await _store.resolve(plain_key)


async def upsert_client(**kwargs) -> None:
    if _store is None:
        raise RuntimeError("Tenant store has not been initialised")
    await _store.upsert_client(**kwargs)


async def list_principals() -> list[Principal]:
    if _store is None:
        raise RuntimeError("Tenant store has not been initialised")
    return await _store.list_principals()


async def delete_client(client_id: str) -> None:
    if _store is None:
        raise RuntimeError("Tenant store has not been initialised")
    await _store.delete_client(client_id)


def reset_store() -> None:
    """Clear the singleton (useful in tests)."""
    global _store
    _store = None
