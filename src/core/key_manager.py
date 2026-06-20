"""Encrypted API key storage using AES-256-GCM and SQLite.

Keys are encrypted at rest and decrypted only in memory at request time.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import aiosqlite
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.core.config_loader import get_config

_KEY_LENGTH = 32
_MASKED_KEY = "\u25cf\u25cf\u25cf\u25cf\u25cf"


def generate_encryption_key() -> bytes:
    """Generate a new 32-byte AES-256-GCM key."""
    return AESGCM.generate_key(bit_length=256)


def _load_encryption_key() -> bytes:
    """Load and validate the ENCRYPTION_KEY from the environment."""
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    b64_key = os.environ.get("ENCRYPTION_KEY")
    if not b64_key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one with:\n"
            "python -c \"from cryptography.hazmat.primitives.ciphers.aead import AESGCM; "
            "import base64; print(base64.b64encode(AESGCM.generate_key(bit_length=256)).decode())\""
        )
    try:
        key = base64.b64decode(b64_key)
    except Exception as exc:
        raise RuntimeError("ENCRYPTION_KEY is not valid base64") from exc
    if len(key) != _KEY_LENGTH:
        raise RuntimeError(
            f"ENCRYPTION_KEY must decode to {_KEY_LENGTH} bytes, got {len(key)}"
        )
    return key


def encrypt_key(plain_key: str, key: bytes) -> str:
    """Encrypt a plaintext key and return base64(nonce + ciphertext)."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plain_key.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_key(encrypted_b64: str, key: bytes) -> str:
    """Decrypt a base64(nonce + ciphertext) key to plaintext."""
    data = base64.b64decode(encrypted_b64)
    nonce, ciphertext = data[:12], data[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")


class KeyManager:
    """Manages encrypted provider API keys in SQLite."""

    def __init__(self) -> None:
        self._encryption_key = _load_encryption_key()
        self._db_path: Path | None = None

    async def init(self) -> None:
        """Create the database and keys table if they do not exist."""
        self._db_path = Path(get_config().database.path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS keys (
                    id TEXT PRIMARY KEY,
                    encrypted_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    health_status TEXT DEFAULT 'unknown'
                )
                """
            )
            await db.commit()

        await self._bootstrap_from_env()

    async def _bootstrap_from_env(self) -> None:
        """Import keys from environment variables when the database is empty."""
        env_var_map = {
            "openrouter": "OPENROUTER_KEY",
            "gemini": "GEMINI_KEY",
            "groq": "GROQ_KEY",
            "mistral": "MISTRAL_KEY",
            "github_models": "GITHUB_KEY",
            "nvidia": "NVIDIA_KEY",
            "cerebras": "CEREBRAS_KEY",
            "cloudflare": "CLOUDFLARE_API_TOKEN",
            "zhipu": "ZHIPU_KEY",
            "huggingface": "HF_KEY",
            "aion": "AION_KEY",
            "cohere": "COHERE_KEY",
        }

        existing = await self.list_providers_with_keys()
        if existing:
            return

        for provider_id, env_var in env_var_map.items():
            value = os.environ.get(env_var)
            if value:
                await self.set_key(provider_id, value)

    async def set_key(self, provider_id: str, plain_key: str) -> None:
        """Encrypt and store a provider API key."""
        encrypted = encrypt_key(plain_key, self._encryption_key)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO keys (id, encrypted_key, health_status)
                VALUES (?, ?, 'unknown')
                ON CONFLICT(id) DO UPDATE SET
                    encrypted_key=excluded.encrypted_key,
                    health_status='unknown'
                """,
                (provider_id, encrypted),
            )
            await db.commit()

    async def get_key(self, provider_id: str) -> str:
        """Return the decrypted API key for a provider."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT encrypted_key FROM keys WHERE id = ?", (provider_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return ""

        plain = decrypt_key(row[0], self._encryption_key)
        await self._touch(provider_id)
        return plain

    async def _touch(self, provider_id: str) -> None:
        """Update the last_used timestamp without exposing the key."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE keys SET last_used = CURRENT_TIMESTAMP WHERE id = ?",
                (provider_id,),
            )
            await db.commit()

    async def delete_key(self, provider_id: str) -> None:
        """Remove a provider's key from storage."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM keys WHERE id = ?", (provider_id,))
            await db.commit()

    async def list_providers_with_keys(self) -> list[str]:
        """Return the ids of all providers with stored keys."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT id FROM keys") as cursor:
                rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def list_key_summaries(self) -> list[dict[str, str]]:
        """Return masked key summaries safe to expose to UI clients."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT id, health_status FROM keys ORDER BY id"
            ) as cursor:
                rows = await cursor.fetchall()
        return [
            {
                "provider": row[0],
                "masked": _MASKED_KEY,
                "health_status": row[1] or "unknown",
            }
            for row in rows
        ]

    async def update_health(self, provider_id: str, status: str) -> None:
        """Update the health status for a provider's key."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE keys SET health_status = ? WHERE id = ?",
                (status, provider_id),
            )
            await db.commit()

    async def get_key_metadata(self, provider_id: str) -> dict[str, Any] | None:
        """Return non-sensitive metadata for a stored key."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT created_at, last_used, health_status FROM keys WHERE id = ?",
                (provider_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "created_at": row[0],
            "last_used": row[1],
            "health_status": row[2],
        }


# Module-level singleton.
_manager: KeyManager | None = None


async def init() -> None:
    """Initialise the module-level key manager."""
    global _manager
    if _manager is None:
        _manager = KeyManager()
    await _manager.init()


async def set_key(provider_id: str, plain_key: str) -> None:
    if _manager is None:
        raise RuntimeError("Key manager has not been initialised")
    await _manager.set_key(provider_id, plain_key)


async def get_key(provider_id: str) -> str:
    if _manager is None:
        raise RuntimeError("Key manager has not been initialised")
    return await _manager.get_key(provider_id)


async def delete_key(provider_id: str) -> None:
    if _manager is None:
        raise RuntimeError("Key manager has not been initialised")
    await _manager.delete_key(provider_id)


async def list_providers_with_keys() -> list[str]:
    if _manager is None:
        raise RuntimeError("Key manager has not been initialised")
    return await _manager.list_providers_with_keys()


async def update_health(provider_id: str, status: str) -> None:
    if _manager is None:
        raise RuntimeError("Key manager has not been initialised")
    await _manager.update_health(provider_id, status)


async def get_key_metadata(provider_id: str) -> dict[str, Any] | None:
    """Return non-sensitive metadata for one stored provider key."""
    if _manager is None:
        raise RuntimeError("Key manager has not been initialised")
    return await _manager.get_key_metadata(provider_id)


async def list_key_summaries() -> list[dict[str, str]]:
    """Return masked key summaries for every stored provider key."""
    if _manager is None:
        raise RuntimeError("Key manager has not been initialised")
    return await _manager.list_key_summaries()
