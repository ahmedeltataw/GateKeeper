"""Dashboard authentication store (scrypt password hashing in SQLite).

The HTML/Jinja dashboard was retired in favour of the standalone Streamlit
panel (see ``dashboard/`` and ``docs/plan/DASHBOARD_ARCHITECTURE.md`` §6). What
remains here is the password store: ``init()`` creates the table and seeds a
password from ``DASHBOARD_PASSWORD`` on first run, and the scrypt helpers are
kept for a future ``/admin/login`` endpoint.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from pathlib import Path

import aiosqlite

from src.core.config_loader import get_config

_DASHBOARD_PASSWORD_ENV = "DASHBOARD_PASSWORD"


def _db_path() -> Path:
    return Path(get_config().database.path)


async def _init_dashboard_table() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboard_auth (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def _has_password() -> bool:
    async with aiosqlite.connect(_db_path()) as db:
        async with db.execute("SELECT COUNT(*) FROM dashboard_auth") as cursor:
            row = await cursor.fetchone()
            return bool(row and row[0] > 0)


async def get_password_hash(username: str) -> str | None:
    """Return the stored scrypt hash for a username, or None if unset."""
    async with aiosqlite.connect(_db_path()) as db:
        async with db.execute(
            "SELECT password_hash FROM dashboard_auth WHERE username = ?",
            (username,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_password(username: str, password: str) -> None:
    """Store (or replace) the scrypt-hashed password for a username."""
    password_hash = hash_password(password)
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            """
            INSERT INTO dashboard_auth (username, password_hash)
            VALUES (?, ?)
            ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash
            """,
            (username, password_hash),
        )
        await db.commit()


def hash_password(password: str) -> str:
    """Return a scrypt hash of the password as a base64 string."""
    salt = os.urandom(32)
    hashed = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
    )
    return base64.b64encode(salt + hashed).decode("ascii")


def verify_password(password: str, stored_hash: str) -> bool:
    """Return whether a plaintext password matches a stored scrypt hash."""
    data = base64.b64decode(stored_hash)
    salt, hashed = data[:32], data[32:]
    candidate = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
    )
    return secrets.compare_digest(hashed, candidate)


async def init() -> None:
    """Create the auth table and seed a password from the environment on first run."""
    await _init_dashboard_table()
    password = os.environ.get(_DASHBOARD_PASSWORD_ENV)
    if password and not await _has_password():
        await set_password(get_config().dashboard.username, password)
