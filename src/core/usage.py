"""Per-tenant usage counters with a write-behind SQLite backend.

Design (see the architecture note): the hot path NEVER touches disk. Every chat
request increments an in-memory counter keyed by ``(client_id, model_id,
period)``; a background task flushes the dirty counters to SQLite every
``flush_seconds`` and once more on shutdown. Reads come straight from memory,
which is seeded from SQLite at startup for the current period — so a restart
keeps absolute counts.

``period`` is a UTC day string (``YYYY-MM-DD``); a new day yields fresh keys, so
daily quotas reset for free. To scale beyond one node, swap the in-memory dict
for Redis ``INCR`` behind this same module interface — routes and UI never
change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.core.config_loader import get_config


def current_period() -> str:
    """Return today's UTC date as the counter period key (``YYYY-MM-DD``)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# In-memory counters: {(client_id, model_id, period): {"requests": int, "tokens": int}}.
_counters: dict[tuple[str, str, str], dict[str, int]] = {}
_dirty: set[tuple[str, str, str]] = set()
_db_path: Path | None = None


def record(client_id: str, model_id: str, tokens: int = 0, requests: int = 1) -> None:
    """Increment the in-memory counter for one client/model in the current period.

    O(1), no IO — safe to call on every request.
    """
    key = (client_id, model_id, current_period())
    entry = _counters.setdefault(key, {"requests": 0, "tokens": 0})
    entry["requests"] += requests
    entry["tokens"] += max(0, tokens)
    _dirty.add(key)


def get_client_usage(client_id: str, period: str | None = None) -> dict[str, dict[str, int]]:
    """Return ``{model_id: {"requests", "tokens"}}`` for one client in a period."""
    period = period or current_period()
    return {
        model_id: dict(counts)
        for (cid, model_id, per), counts in _counters.items()
        if cid == client_id and per == period
    }


def get_all_usage(period: str | None = None) -> dict[str, dict[str, dict[str, int]]]:
    """Return ``{client_id: {model_id: {...}}}`` for every client in a period."""
    period = period or current_period()
    result: dict[str, dict[str, dict[str, int]]] = {}
    for (client_id, model_id, per), counts in _counters.items():
        if per == period:
            result.setdefault(client_id, {})[model_id] = dict(counts)
    return result


async def init() -> None:
    """Create the usage table and seed memory with the current period's rows."""
    global _db_path
    _db_path = Path(get_config().database.path)
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_counters (
                client_id  TEXT NOT NULL,
                model_id   TEXT NOT NULL,
                period     TEXT NOT NULL,
                requests   INTEGER NOT NULL DEFAULT 0,
                tokens     INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (client_id, model_id, period)
            )
            """
        )
        await db.commit()
    await _seed_current_period()


async def _seed_current_period() -> None:
    """Load the current period's persisted counters into memory after a restart."""
    if _db_path is None:
        return
    period = current_period()
    async with aiosqlite.connect(_db_path) as db:
        async with db.execute(
            "SELECT client_id, model_id, requests, tokens "
            "FROM usage_counters WHERE period = ?",
            (period,),
        ) as cursor:
            rows = await cursor.fetchall()
    for client_id, model_id, requests, tokens in rows:
        _counters[(client_id, model_id, period)] = {
            "requests": int(requests),
            "tokens": int(tokens),
        }


async def flush() -> None:
    """Write all dirty counters to SQLite (absolute values) and prune old periods."""
    if _db_path is None or not _dirty:
        _prune_old_periods()
        return

    pending = list(_dirty)
    _dirty.clear()
    async with aiosqlite.connect(_db_path) as db:
        await db.executemany(
            """
            INSERT INTO usage_counters (client_id, model_id, period, requests, tokens)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(client_id, model_id, period) DO UPDATE SET
                requests=excluded.requests,
                tokens=excluded.tokens
            """,
            [
                (cid, mid, per, _counters[(cid, mid, per)]["requests"],
                 _counters[(cid, mid, per)]["tokens"])
                for (cid, mid, per) in pending
                if (cid, mid, per) in _counters
            ],
        )
        await db.commit()
    _prune_old_periods()


def _prune_old_periods() -> None:
    """Drop in-memory counters from past periods to bound memory growth.

    Already-flushed, so the durable copy survives in SQLite for history/billing.
    """
    period = current_period()
    stale = [key for key in _counters if key[2] != period and key not in _dirty]
    for key in stale:
        del _counters[key]


def reset() -> None:
    """Clear in-memory state. Test isolation only."""
    _counters.clear()
    _dirty.clear()


def reset_store() -> None:
    """Clear the db path binding. Test isolation only."""
    global _db_path
    _db_path = None
