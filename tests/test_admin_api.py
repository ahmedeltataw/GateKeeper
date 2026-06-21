"""Tests for the HTTP/JSON admin API."""

from __future__ import annotations

import base64
import sqlite3
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.server import create_app
from src.core import key_manager, rate_limiter
from src.core import config_loader
from src.core.registry import reset_registry
from src.core.router import reset_providers

@pytest_asyncio.fixture
async def admin_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create an app client with an isolated database and admin token."""
    config_path = tmp_path / "config.yaml"
    database_path = tmp_path / "gateway.db"
    state_path = tmp_path / "rate_limits.json"
    config_path.write_text(
        "\n".join(
            [
                'server:',
                '  host: "127.0.0.1"',
                '  port: 8000',
                '  workers: 1',
                '  log_level: "INFO"',
                '  cors_origins: ["*"]',
                'auth:',
                '  enabled: true',
                '  api_key: "sk-local"',
                'database:',
                f'  path: "{database_path.as_posix()}"',
                'cache:',
                '  enabled: true',
                '  ttl: 300',
                '  max_size: 1000',
                'rate_limiter:',
                f'  state_file: "{state_path.as_posix()}"',
                '  enabled: true',
                'sticky_sessions:',
                '  enabled: true',
                '  ttl: 1800',
                '  context_handoff: true',
                'quality_router:',
                '  enabled: true',
                '  default_task_type: "default"',
                'providers: {}',
                'dashboard:',
                '  enabled: true',
                '  username: "admin"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", config_path)
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
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
        yield client, database_path

    config_loader.get_config.cache_clear()
    key_manager._manager = None
    reset_registry()
    await reset_providers()
    rate_limiter._buckets.clear()


@pytest.mark.asyncio
async def test_admin_providers_returns_403_when_token_unset(
    admin_client: tuple[AsyncClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Admin routes reject every request when ADMIN_TOKEN is not configured."""
    client, _ = admin_client
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    # Stop get_config() from re-reading the developer's real .env (which now has
    # ADMIN_TOKEN); this test must see the token genuinely unset.
    monkeypatch.setattr(config_loader, "load_dotenv", lambda *args, **kwargs: None)
    config_loader.get_config.cache_clear()

    response = await client.get("/admin/providers")

    assert response.status_code == 403
    assert response.json() == {"error": "admin token not configured"}


@pytest.mark.asyncio
async def test_admin_providers_auth_states(admin_client: tuple[AsyncClient, Path]) -> None:
    """Admin provider status endpoint returns 401 or 200 for bad and good tokens."""
    client, _ = admin_client

    bad_response = await client.get(
        "/admin/providers",
        headers={"Authorization": "Bearer WRONG"},
    )
    good_response = await client.get(
        "/admin/providers",
        headers={"Authorization": "Bearer test-admin-token"},
    )

    assert bad_response.status_code == 401
    assert good_response.status_code == 200
    assert good_response.json() == []


@pytest.mark.asyncio
async def test_admin_key_write_stores_ciphertext_and_returns_masked_summary(
    admin_client: tuple[AsyncClient, Path]
) -> None:
    """Posting a key encrypts it at rest and never returns the plaintext value."""
    client, database_path = admin_client
    headers = {"Authorization": "Bearer test-admin-token"}

    create_response = await client.post(
        "/admin/keys",
        headers=headers,
        json={"provider": "groq", "api_key": "gsk_test_123"},
    )
    list_response = await client.get("/admin/keys", headers=headers)

    assert create_response.status_code == 201
    assert create_response.json() == {
        "provider": "groq",
        "masked": "●●●●●",
        "health_status": "unknown",
    }
    assert list_response.status_code == 200
    assert list_response.json() == [
        {"provider": "groq", "masked": "●●●●●", "health_status": "unknown"}
    ]
    assert "gsk_test_123" not in list_response.text

    encrypted_value = sqlite3.connect(database_path).execute(
        "SELECT encrypted_key FROM keys WHERE id = ?",
        ("groq",),
    ).fetchone()[0]
    assert encrypted_value != "gsk_test_123"
    assert "gsk_test_123" not in encrypted_value


@pytest.mark.asyncio
async def test_admin_enable_disable_and_retry_model(
    admin_client: tuple[AsyncClient, Path]
) -> None:
    """Admin can toggle a model and clear its breaker at runtime (no restart)."""
    client, _ = admin_client
    headers = {"Authorization": "Bearer test-admin-token"}
    model_id = "gemini-2.5-flash"  # stable doc-verified id

    disable = await client.post(f"/admin/models/{model_id}/disable", headers=headers)
    assert disable.status_code == 200
    assert disable.json() == {"id": model_id, "enabled": False}

    # Disabled model drops out of the public catalog.
    listing = await client.get("/v1/models", headers={"X-API-Key": "sk-local"})
    assert model_id not in [m["id"] for m in listing.json()["data"]]

    enable = await client.post(f"/admin/models/{model_id}/enable", headers=headers)
    assert enable.status_code == 200
    assert enable.json()["enabled"] is True
    assert enable.json()["circuit"] == "reset"

    retry = await client.post(f"/admin/models/{model_id}/retry", headers=headers)
    assert retry.status_code == 200
    assert retry.json()["circuit"] == "reset"


@pytest.mark.asyncio
async def test_admin_model_controls_404_on_unknown(
    admin_client: tuple[AsyncClient, Path]
) -> None:
    client, _ = admin_client
    headers = {"Authorization": "Bearer test-admin-token"}
    for verb in ("enable", "disable", "retry"):
        resp = await client.post(f"/admin/models/nope-not-real/{verb}", headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_quarantine_shape(admin_client: tuple[AsyncClient, Path]) -> None:
    client, _ = admin_client
    headers = {"Authorization": "Bearer test-admin-token"}
    resp = await client.get("/admin/quarantine", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "quarantined" in body and isinstance(body["quarantined"], list)
    assert "last_probe" in body


@pytest.mark.asyncio
async def test_admin_routes_are_not_mounted_when_dashboard_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disabling the dashboard removes the admin router instead of auth-blocking it."""
    config_path = tmp_path / "config.yaml"
    database_path = tmp_path / "gateway.db"
    state_path = tmp_path / "rate_limits.json"
    config_path.write_text(
        "\n".join(
            [
                'server:',
                '  host: "127.0.0.1"',
                '  port: 8000',
                '  workers: 1',
                '  log_level: "INFO"',
                '  cors_origins: ["*"]',
                'auth:',
                '  enabled: true',
                '  api_key: "sk-local"',
                'database:',
                f'  path: "{database_path.as_posix()}"',
                'cache:',
                '  enabled: true',
                '  ttl: 300',
                '  max_size: 1000',
                'rate_limiter:',
                f'  state_file: "{state_path.as_posix()}"',
                '  enabled: true',
                'sticky_sessions:',
                '  enabled: true',
                '  ttl: 1800',
                '  context_handoff: true',
                'quality_router:',
                '  enabled: true',
                '  default_task_type: "default"',
                'providers: {}',
                'dashboard:',
                '  enabled: false',
                '  username: "admin"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_loader, "_CONFIG_PATH", config_path)
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv(
        "ENCRYPTION_KEY",
        base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("ascii"),
    )
    config_loader.get_config.cache_clear()
    key_manager._manager = None
    reset_registry()
    await reset_providers()
    rate_limiter._buckets.clear()
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get(
            "/admin/providers",
            headers={"Authorization": "Bearer test-admin-token"},
        )

    assert response.status_code == 404
