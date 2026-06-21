"""Tests for onboarding endpoints: connection-info, agent-snippet, X-API-Key."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_connection_info_public_and_self_describing(test_app, loaded_registry):
    # No Authorization header — endpoint must be public.
    resp = await test_app.get("/v1/connection-info")
    assert resp.status_code == 200
    doc = resp.json()

    assert doc["gateway"]["base_url"].endswith("/v1")
    # Loopback default bind -> key is echoed for local onboarding.
    assert doc["gateway"]["api_key"] == "sk-local"
    assert doc["models"]["default"] == "auto"
    assert "auto" in doc["models"]["sample_ids"]
    assert "opencode" in doc["agents"]
    assert "claude-code" in doc["agents"]


@pytest.mark.asyncio
async def test_agent_snippet_text(test_app):
    resp = await test_app.get("/v1/agent-snippet", params={"agent": "opencode"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent"] == "opencode"
    assert body["format"] == "text"
    assert "OPENAI_BASE_URL" in body["snippet"]
    assert "sk-local" in body["snippet"]


@pytest.mark.asyncio
async def test_agent_snippet_json(test_app):
    resp = await test_app.get(
        "/v1/agent-snippet", params={"agent": "claude-code", "format": "json"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["format"] == "json"
    assert body["config"]["type"] == "env"
    assert body["config"]["vars"]["ANTHROPIC_API_KEY"] == "sk-local"


@pytest.mark.asyncio
async def test_agent_snippet_unknown_agent_is_400(test_app):
    resp = await test_app.get("/v1/agent-snippet", params={"agent": "nope"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_x_api_key_header_accepted(test_app, loaded_registry):
    # A protected route must accept X-API-Key in place of Authorization: Bearer.
    resp = await test_app.get("/v1/models", headers={"X-API-Key": "sk-local"})
    assert resp.status_code == 200

    # Wrong key is still rejected.
    bad = await test_app.get("/v1/models", headers={"X-API-Key": "wrong"})
    assert bad.status_code == 401
