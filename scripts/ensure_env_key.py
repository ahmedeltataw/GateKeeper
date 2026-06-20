"""Ensure a local ``.env`` exists and contains a valid ``ENCRYPTION_KEY``.

Run on every launch (see ``run.bat``). It is idempotent:

* if ``.env`` is missing, it is created from ``.env.example`` (or empty);
* if ``ENCRYPTION_KEY`` is absent or still the placeholder, a fresh AES-256-GCM
  key is generated and written **into the local ``.env``** — so the secret lives
  only on this machine and never in an external file or the repository.

Existing keys are left untouched, so provider keys and a previously generated
encryption key are never overwritten.
"""

from __future__ import annotations

import base64
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_PATH = _PROJECT_ROOT / ".env"
_ENV_EXAMPLE = _PROJECT_ROOT / ".env.example"
_PLACEHOLDER = "YOUR_32_BYTE_BASE64_KEY_HERE"


def _generate_key() -> str:
    """Return a fresh base64-encoded AES-256-GCM key."""
    return base64.b64encode(AESGCM.generate_key(bit_length=256)).decode("ascii")


def _read_lines() -> list[str]:
    """Return the current .env lines, seeding from .env.example on first run."""
    if _ENV_PATH.exists():
        return _ENV_PATH.read_text(encoding="utf-8").splitlines()
    if _ENV_EXAMPLE.exists():
        return _ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    return []


def _has_real_key(lines: list[str]) -> bool:
    """True if an ENCRYPTION_KEY line holds a real (non-placeholder) value."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("ENCRYPTION_KEY="):
            value = stripped.split("=", 1)[1].strip()
            return bool(value) and value != _PLACEHOLDER
    return False


def ensure_key() -> bool:
    """Guarantee .env has a usable ENCRYPTION_KEY. Returns True if one was added."""
    lines = _read_lines()

    if _has_real_key(lines):
        # Make sure the file exists on disk even if we only read the example.
        if not _ENV_PATH.exists():
            _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return False

    new_key = _generate_key()
    replaced = False
    output: list[str] = []
    for line in lines:
        if line.strip().startswith("ENCRYPTION_KEY="):
            output.append(f"ENCRYPTION_KEY={new_key}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"ENCRYPTION_KEY={new_key}")

    _ENV_PATH.write_text("\n".join(output).rstrip("\n") + "\n", encoding="utf-8")
    return True


if __name__ == "__main__":
    created = ensure_key()
    if created:
        print("[setup] Generated a new ENCRYPTION_KEY and saved it to .env (local only).")
    else:
        print("[setup] ENCRYPTION_KEY already present in .env.")
