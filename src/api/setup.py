"""First-run onboarding endpoints for admin access.

Before any ``ADMIN_TOKEN`` exists, the dashboard cannot authenticate to
``/admin/*`` and would otherwise be a dead end. This router exposes two
narrowly-scoped, *public* endpoints under ``/admin/setup`` so a first-time user
can mint their access key from the dashboard:

* ``GET  /admin/setup/status``    — does the gateway still need a key?
* ``POST /admin/setup/bootstrap`` — mint a ``gk_...`` key **once**, persist it
  to ``.env`` when possible, and start enforcing it immediately.

Security model (see also ``src/api/middleware.py``):

* ``bootstrap`` mints a key **only while none is configured**. Once a token
  exists it returns ``409`` and the middleware stops treating it as public, so
  it can never be used to rotate or overwrite an existing key.
* ``bootstrap`` is refused for any non-loopback caller (``403``). The gateway
  normally binds ``127.0.0.1``, but behind a reverse proxy or in a container
  with a published port the bind alone is not a guarantee, so the endpoint
  enforces the loopback constraint itself.
* The plaintext token is returned exactly once and never logged.

Container/Docker behavior:

* ``.env`` is frequently mounted read-only (or not present) in containers.
  ``bootstrap`` probes for write access first; when the file cannot be written
  it falls back to a **process-only** token (set in ``os.environ``) and tells
  the caller to persist ``ADMIN_TOKEN`` via the container's environment so it
  survives a restart. The endpoint never crashes on a read-only filesystem.
* The recommended container setup skips ``bootstrap`` entirely: inject
  ``ADMIN_TOKEN`` as an environment variable and ``setup/status`` reports
  ``needs_setup: false`` from the first boot.
"""

from __future__ import annotations

import asyncio
import os
import secrets
from pathlib import Path

from dotenv import set_key
from fastapi import APIRouter, HTTPException, Request, status

from src.core.config_loader import get_config, reload_config

router = APIRouter(prefix="/admin/setup", tags=["setup"])

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_TOKEN_PREFIX = "gk_"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

# Serializes concurrent bootstrap calls so only one key is ever generated.
_bootstrap_lock = asyncio.Lock()


def _env_path() -> Path:
    """Return the project-root ``.env`` path (patched to a temp file in tests)."""
    return _ENV_PATH


def _generate_token() -> str:
    """Return a strong, URL-safe admin token in ``gk_<random>`` format."""
    return _TOKEN_PREFIX + secrets.token_urlsafe(32)


def _admin_token_configured() -> bool:
    """Return whether an admin token is currently configured."""
    return bool(get_config().dashboard.admin_token)


def _is_loopback(request: Request) -> bool:
    """Return whether the request originated from the local machine.

    Trusts only the transport peer (``request.client``), never proxy headers
    such as ``X-Forwarded-For``, which a remote caller can forge.
    """
    client = request.client
    return client is not None and client.host in _LOOPBACK_HOSTS


def _env_is_writable(env_path: Path) -> bool:
    """Best-effort probe of whether ``ADMIN_TOKEN`` can be persisted to ``.env``.

    Checks the file when it exists, otherwise the parent directory (where the
    file would be created). This is advisory only — the actual write is still
    guarded — so a read-only Docker mount degrades gracefully instead of raising.
    """
    if env_path.exists():
        return os.access(env_path, os.W_OK)
    parent = env_path.parent
    return parent.is_dir() and os.access(parent, os.W_OK)


def _persist_token(env_path: Path, token: str) -> bool:
    """Try to write ``ADMIN_TOKEN`` to ``.env``; return whether it was persisted.

    Returns ``False`` (never raises) on any filesystem error so a read-only or
    missing ``.env`` cannot break first-run setup. The token is still applied to
    the running process by the caller regardless of the outcome here.
    """
    if not _env_is_writable(env_path):
        return False
    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.touch(exist_ok=True)
        # set_key rewrites only the ADMIN_TOKEN line and preserves every other var.
        set_key(str(env_path), "ADMIN_TOKEN", token, quote_mode="never")
        return True
    except OSError:
        # Read-only mount, race on permissions, etc. Fall back to env-only.
        return False


@router.get("/status")
async def setup_status() -> dict[str, bool]:
    """Report whether the gateway still needs an admin key (public, read-only)."""
    return {"needs_setup": not _admin_token_configured()}


@router.post("/bootstrap")
async def setup_bootstrap(request: Request) -> dict[str, str | bool]:
    """Mint and apply the admin token once; persist to ``.env`` when writable."""
    # Guard: first-run minting is local-only, independent of the network bind.
    if not _is_loopback(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="setup is only available from localhost",
        )

    async with _bootstrap_lock:
        # Re-check inside the lock: a racing caller may have just configured it.
        if _admin_token_configured():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="admin token already configured",
            )

        token = _generate_token()
        persisted = _persist_token(_env_path(), token)

        # Apply to the running process so the token is enforced on the next
        # request, whether or not it reached disk.
        os.environ["ADMIN_TOKEN"] = token
        reload_config()

    response: dict[str, str | bool] = {"admin_token": token, "persisted": persisted}
    if not persisted:
        # Read-only/containerized .env: tell the operator how to make it stick.
        response["hint"] = (
            "Could not write .env (read-only filesystem?). The token is active "
            "for this process only. Set ADMIN_TOKEN in the environment to "
            "persist it across restarts."
        )
    return response
