"""Tests for the first-run onboarding endpoints (`/admin/setup/*`)."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api import setup
from src.api.server import create_app
from src.core import config_loader, key_manager, rate_limiter
from src.core.registry import reset_registry
from src.core.router import reset_providers

_CONFIG_YAML = "\n".join(
    [
        'server:',
        '  host: "127.0.0.1"',
        '  port: 8000',
        '  log_level: "INFO"',
        '  cors_origins: ["*"]',
        'auth:',
        '  enabled: true',
        '  api_key: "sk-local"',
        'database:',
        '  path: "{database}"',
        'rate_limiter:',
        '  state_file: "{state}"',
        '  enabled: true',
        'providers: {{}}',
        'dashboard:',
        '  enabled: true',
        '  username: "admin"',
    ]
)


@pytest_asyncio.fixture
async def first_run_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """App client that starts with NO admin token configured (genuine first run)."""
    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / ".env"
    config_path.write_text(
        _CONFIG_YAML.format(
            database=(tmp_path / "gateway.db").as_posix(),
            state=(tmp_path / "rate_limits.json").as_posix(),
        ),
        encoding="utf-8",
    )
    # A pre-existing variable that the .env write must preserve.
    env_path.write_text("EXISTING=keepme\n", encoding="utf-8")

    monkeypatch.setattr(config_loader, "_CONFIG_PATH", config_path)
    monkeypatch.setattr(setup, "_ENV_PATH", env_path)
    # Never read the developer's real .env (which has a real ADMIN_TOKEN). Patch
    # both the config_loader reference and dotenv itself, since key_manager.init()
    # does its own `from dotenv import load_dotenv` and would re-populate os.environ.
    monkeypatch.setattr(config_loader, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.setenv(
        "ENCRYPTION_KEY",
        base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("ascii"),
    )

    async def _skip_bootstrap(self) -> None:
        return None

    monkeypatch.setattr(key_manager.KeyManager, "_bootstrap_from_env", _skip_bootstrap)
    config_loader.get_config.cache_clear()
    key_manager._manager = None
    reset_registry()
    await reset_providers()
    rate_limiter._buckets.clear()
    await key_manager.init()

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client, env_path

    # bootstrap writes os.environ["ADMIN_TOKEN"] directly; undo it for other tests.
    os.environ.pop("ADMIN_TOKEN", None)
    config_loader.get_config.cache_clear()
    key_manager._manager = None
    reset_registry()
    await reset_providers()
    rate_limiter._buckets.clear()


@pytest.mark.asyncio
async def test_status_is_public_and_reports_needs_setup(first_run_client) -> None:
    """Status is reachable without a token and reports setup is required."""
    client, _ = first_run_client

    response = await client.get("/admin/setup/status")

    assert response.status_code == 200
    assert response.json() == {"needs_setup": True}


@pytest.mark.asyncio
async def test_other_admin_routes_still_blocked_before_setup(first_run_client) -> None:
    """Only the setup paths are public; the rest of /admin stays locked at 403."""
    client, _ = first_run_client

    response = await client.get("/admin/providers")

    assert response.status_code == 403
    assert response.json() == {"error": "admin token not configured"}


@pytest.mark.asyncio
async def test_bootstrap_mints_persists_and_enforces(first_run_client) -> None:
    """Bootstrap mints a gk_ key, preserves other .env vars, and enforces it."""
    client, env_path = first_run_client

    boot = await client.post("/admin/setup/bootstrap")
    assert boot.status_code == 200
    token = boot.json()["admin_token"]
    assert token.startswith("gk_")
    assert len(token) > 20

    # .env keeps the existing var and gains ADMIN_TOKEN.
    env_text = env_path.read_text(encoding="utf-8")
    assert "EXISTING=keepme" in env_text
    assert f"ADMIN_TOKEN={token}" in env_text
    assert os.environ["ADMIN_TOKEN"] == token

    # Setup is now complete.
    status_after = await client.get("/admin/setup/status")
    assert status_after.json() == {"needs_setup": False}

    # The new token is enforced immediately, with no restart.
    unauth = await client.get("/admin/providers")
    assert unauth.status_code == 401
    good = await client.get("/admin/providers", headers={"Authorization": f"Bearer {token}"})
    assert good.status_code == 200


@pytest.mark.asyncio
async def test_bootstrap_is_one_shot(first_run_client) -> None:
    """A second bootstrap is rejected (no silent key rotation)."""
    client, _ = first_run_client

    first = await client.post("/admin/setup/bootstrap")
    token = first.json()["admin_token"]

    # Once configured, bootstrap is no longer public: needs the token, then 409.
    without_token = await client.post("/admin/setup/bootstrap")
    assert without_token.status_code == 401

    with_token = await client.post(
        "/admin/setup/bootstrap", headers={"Authorization": f"Bearer {token}"}
    )
    assert with_token.status_code == 409


@pytest.mark.asyncio
async def test_bootstrap_falls_back_when_env_unwritable(
    first_run_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read-only .env (Docker) yields a process-only token, never a 500."""
    client, env_path = first_run_client
    monkeypatch.setattr(setup, "_env_is_writable", lambda _path: False)

    boot = await client.post("/admin/setup/bootstrap")

    assert boot.status_code == 200
    body = boot.json()
    token = body["admin_token"]
    assert token.startswith("gk_")
    assert body["persisted"] is False
    assert "hint" in body
    # File untouched, but the token is enforced for the running process.
    assert "ADMIN_TOKEN" not in env_path.read_text(encoding="utf-8")
    assert os.environ["ADMIN_TOKEN"] == token

    good = await client.get("/admin/providers", headers={"Authorization": f"Bearer {token}"})
    assert good.status_code == 200


@pytest.mark.asyncio
async def test_bootstrap_rejects_non_loopback_caller(
    first_run_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A remote caller cannot mint the first key even before any token exists."""
    client, _ = first_run_client
    monkeypatch.setattr(setup, "_is_loopback", lambda _request: False)

    boot = await client.post("/admin/setup/bootstrap")

    assert boot.status_code == 403
    assert "ADMIN_TOKEN" not in os.environ
