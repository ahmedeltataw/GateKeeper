"""Per-model circuit breaker with auto-blacklist.

This is the "cleanup" layer. Instead of deleting models from the source
``models_registry.json`` (destructive, unrecoverable), each model carries a
runtime breaker state persisted in SQLite:

- ``closed``      — healthy, routable.
- ``open``        — too many consecutive failures; skipped until a cooldown lets
                    one trial request through (half-open).
- ``blacklisted`` — opened too many times; permanently skipped until manually
                    reset. A human-readable report explains why.

The router/fallback consults :func:`is_open`; failures and successes are fed
back via :func:`record_failure` / :func:`record_success`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import aiosqlite

from src.core.config_loader import get_config

STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_BLACKLISTED = "blacklisted"


class _ModelBreaker:
    """In-memory breaker state for one model."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.state = STATE_CLOSED
        self.consecutive_failures = 0
        self.open_count = 0
        self.last_code = ""
        self.last_detail = ""
        self.opened_until = 0.0
        self.blacklist_reason = ""

    def to_row(self) -> tuple[Any, ...]:
        return (
            self.model_id,
            self.state,
            self.consecutive_failures,
            self.open_count,
            self.last_code,
            self.last_detail,
            self.opened_until,
            self.blacklist_reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "state": self.state,
            "consecutive_failures": self.consecutive_failures,
            "open_count": self.open_count,
            "last_code": self.last_code,
            "last_detail": self.last_detail,
            "blacklist_reason": self.blacklist_reason,
        }


_breakers: dict[str, _ModelBreaker] = {}


def _cfg():
    return get_config().circuit


def _db_path() -> Path:
    return Path(get_config().database.path)


def _get(model_id: str) -> _ModelBreaker:
    breaker = _breakers.get(model_id)
    if breaker is None:
        breaker = _ModelBreaker(model_id)
        _breakers[model_id] = breaker
    return breaker


def is_open(model_id: str) -> bool:
    """Return whether routing to this model is currently blocked.

    A blacklisted model is always blocked. An open model is blocked until its
    cooldown elapses, after which one trial request is allowed (half-open).
    """
    if not _cfg().enabled:
        return False
    breaker = _breakers.get(model_id)
    if breaker is None or breaker.state == STATE_CLOSED:
        return False
    if breaker.state == STATE_BLACKLISTED:
        return True
    # open: blocked only until the cooldown window passes.
    return time.time() < breaker.opened_until


async def record_success(model_id: str) -> None:
    """Reset a model's breaker after a successful call (closes half-open)."""
    breaker = _breakers.get(model_id)
    if breaker is None or breaker.state == STATE_BLACKLISTED:
        return
    if breaker.state != STATE_CLOSED or breaker.consecutive_failures:
        breaker.state = STATE_CLOSED
        breaker.consecutive_failures = 0
        await _persist(breaker)


async def record_failure(model_id: str, code: str, detail: str) -> None:
    """Record a failure and advance the breaker state machine."""
    cfg = _cfg()
    if not cfg.enabled:
        return
    breaker = _get(model_id)
    breaker.last_code = code
    breaker.last_detail = detail

    if breaker.state == STATE_BLACKLISTED:
        return

    breaker.consecutive_failures += 1
    if breaker.consecutive_failures >= cfg.failures_to_open:
        breaker.open_count += 1
        breaker.consecutive_failures = 0
        if breaker.open_count >= cfg.opens_to_blacklist:
            breaker.state = STATE_BLACKLISTED
            breaker.blacklist_reason = (
                f"opened {breaker.open_count} times; last error [{code}] {detail}"
            )
            await _write_report(breaker)
        else:
            breaker.state = STATE_OPEN
            breaker.opened_until = time.time() + cfg.open_cooldown_seconds

    await _persist(breaker)


def snapshot() -> dict[str, dict[str, Any]]:
    """Return a copy of every known breaker state (for the catalog/UI)."""
    return {mid: b.to_dict() for mid, b in _breakers.items()}


async def reset(model_id: str) -> None:
    """Manually clear a model's breaker (e.g. after fixing the root cause)."""
    breaker = _breakers.get(model_id)
    if breaker is None:
        return
    breaker.state = STATE_CLOSED
    breaker.consecutive_failures = 0
    breaker.open_count = 0
    breaker.blacklist_reason = ""
    await _persist(breaker)


def reset_all() -> None:
    """Drop all in-memory breaker state (test isolation)."""
    _breakers.clear()


async def init() -> None:
    """Create the SQLite table and load persisted breaker state."""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS model_circuit (
                model_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                consecutive_failures INTEGER NOT NULL,
                open_count INTEGER NOT NULL,
                last_code TEXT,
                last_detail TEXT,
                opened_until REAL,
                blacklist_reason TEXT
            )
            """
        )
        await db.commit()
        async with db.execute(
            "SELECT model_id, state, consecutive_failures, open_count, "
            "last_code, last_detail, opened_until, blacklist_reason FROM model_circuit"
        ) as cursor:
            rows = await cursor.fetchall()

    for row in rows:
        breaker = _ModelBreaker(row[0])
        breaker.state = row[1]
        breaker.consecutive_failures = row[2]
        breaker.open_count = row[3]
        breaker.last_code = row[4] or ""
        breaker.last_detail = row[5] or ""
        breaker.opened_until = row[6] or 0.0
        breaker.blacklist_reason = row[7] or ""
        _breakers[breaker.model_id] = breaker


async def _persist(breaker: _ModelBreaker) -> None:
    """Write one breaker's state to SQLite (best-effort)."""
    try:
        async with aiosqlite.connect(_db_path()) as db:
            await db.execute(
                """
                INSERT INTO model_circuit
                    (model_id, state, consecutive_failures, open_count,
                     last_code, last_detail, opened_until, blacklist_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    state=excluded.state,
                    consecutive_failures=excluded.consecutive_failures,
                    open_count=excluded.open_count,
                    last_code=excluded.last_code,
                    last_detail=excluded.last_detail,
                    opened_until=excluded.opened_until,
                    blacklist_reason=excluded.blacklist_reason
                """,
                breaker.to_row(),
            )
            await db.commit()
    except Exception:
        # Persistence is best-effort; never fail a request over it.
        pass


async def _write_report(breaker: _ModelBreaker) -> None:
    """Append a human-readable blacklist report explaining the failure."""
    try:
        path = Path(_cfg().report_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        entry = (
            f"## {breaker.model_id} — BLACKLISTED ({stamp} UTC)\n"
            f"- Opened {breaker.open_count} time(s) before blacklisting.\n"
            f"- Last error: [{breaker.last_code}] {breaker.last_detail}\n"
            f"- Reason: {breaker.blacklist_reason}\n"
            f"- Remediation already attempted by the diagnostics engine; the "
            f"failure was not programmatically recoverable.\n\n"
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(entry)
    except Exception:
        pass
