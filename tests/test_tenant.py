"""Tests for the multi-tenant entitlement layer.

Covers the four guarantees from the design:
  * OWNER principal sees everything (legacy / auth-disabled behavior).
  * a regular ("auto") principal cannot see dedicated models.
  * an enterprise principal sees dedicated models via tier or explicit allocation.
  * the /v1/models endpoint filters by principal, and the chat entitlement gate
    does NOT restrict failover (failover/circuit operate on the full registry).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.api.routes import chat_completions, list_models, list_models_opencode
from src.core import router as router_mod
from src.core.registry import get_registry
from src.core.tenant import OWNER, Principal, TenantStore, hash_key
from src.core.types import ChatRequest, ChatResponse, Message, ProviderError
from src.providers.base import ProviderConfig
from tests.conftest import FakeProvider


# --- fakes -----------------------------------------------------------------

class _FakeRequest:
    """Minimal stand-in for a Starlette Request used by the route handlers."""

    def __init__(self, principal: Principal | None) -> None:
        self.state = SimpleNamespace()
        if principal is not None:
            self.state.principal = principal
        self.headers: dict[str, str] = {}


def _regular() -> Principal:
    return Principal(client_id="c1", plan="free", allowed_tiers=frozenset({"auto"}))


def _enterprise_tier() -> Principal:
    return Principal(
        client_id="c2", plan="enterprise",
        allowed_tiers=frozenset({"auto", "dedicated"}),
    )


def _enterprise_explicit() -> Principal:
    return Principal(
        client_id="c3", plan="enterprise",
        allowed_tiers=frozenset({"auto"}),
        allowed_model_ids=frozenset({"gh-gpt-4.1"}),
    )


# --- Principal.can_see -----------------------------------------------------

@pytest.mark.asyncio
async def test_owner_sees_all_models(loaded_registry):
    for model in loaded_registry.all_models():
        assert OWNER.can_see(model) is True


@pytest.mark.asyncio
async def test_regular_principal_hides_dedicated(loaded_registry):
    dedicated = loaded_registry.get("gh-gpt-4.1")
    auto = loaded_registry.get("or-gpt-oss-120b")
    assert dedicated is not None and dedicated.tier == "dedicated"
    assert auto is not None and auto.tier == "auto"

    principal = _regular()
    assert principal.can_see(auto) is True
    assert principal.can_see(dedicated) is False


@pytest.mark.asyncio
async def test_enterprise_sees_dedicated_by_tier(loaded_registry):
    dedicated = loaded_registry.get("gh-gpt-4.1")
    assert _enterprise_tier().can_see(dedicated) is True


@pytest.mark.asyncio
async def test_enterprise_sees_dedicated_by_explicit_allocation(loaded_registry):
    dedicated = loaded_registry.get("gh-gpt-4.1")
    other_auto = loaded_registry.get("or-gpt-oss-120b")
    principal = _enterprise_explicit()
    assert principal.can_see(dedicated) is True       # explicit grant
    assert principal.can_see(other_auto) is True       # via "auto" tier


# --- /v1/models filtering --------------------------------------------------

@pytest.mark.asyncio
async def test_models_endpoint_filters_for_regular(loaded_registry):
    await get_registry()
    result = await list_models(task_type=None, http_request=_FakeRequest(_regular()))
    ids = {m["id"] for m in result["data"]}
    assert "gh-gpt-4.1" not in ids          # dedicated hidden
    assert "or-gpt-oss-120b" in ids          # auto visible


@pytest.mark.asyncio
async def test_models_endpoint_owner_sees_dedicated(loaded_registry):
    await get_registry()
    result = await list_models(task_type=None, http_request=_FakeRequest(OWNER))
    ids = {m["id"] for m in result["data"]}
    assert "gh-gpt-4.1" in ids


@pytest.mark.asyncio
async def test_models_endpoint_defaults_to_owner_without_principal(loaded_registry):
    """Missing request.state.principal must default to OWNER, never crash."""
    await get_registry()
    result = await list_models(task_type=None, http_request=_FakeRequest(None))
    assert any(m["id"] == "gh-gpt-4.1" for m in result["data"])


# --- /v1/opencode/models ---------------------------------------------------

@pytest.mark.asyncio
async def test_opencode_shape_and_filter_for_regular(loaded_registry):
    await get_registry()
    result = await list_models_opencode(_FakeRequest(_regular()))

    # Shape: {"models": {id: {"name": ...}}} — models is an object, not a list.
    assert isinstance(result["models"], dict)
    sample_id, entry = next(iter(result["models"].items()))
    assert set(entry.keys()) == {"name"}            # name only, no technical data
    assert entry["name"]

    assert "gh-gpt-4.1" not in result["models"]      # dedicated hidden
    assert "or-gpt-oss-120b" in result["models"]      # auto visible


@pytest.mark.asyncio
async def test_opencode_owner_sees_dedicated(loaded_registry):
    await get_registry()
    result = await list_models_opencode(_FakeRequest(OWNER))
    assert "gh-gpt-4.1" in result["models"]


# --- chat entitlement gate -------------------------------------------------

@pytest.mark.asyncio
async def test_chat_gate_blocks_dedicated_for_regular(loaded_registry):
    request = ChatRequest(
        model="gh-gpt-4.1", messages=[Message(role="user", content="hi")]
    )
    response = await chat_completions(request, _FakeRequest(_regular()))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_chat_gate_does_not_break_failover(loaded_registry):
    """A regular client requesting an AUTO model still gets a response via the
    fallback engine — the gate only checks the entry model, so failover (which
    runs on the full registry) is unaffected."""
    router_mod._provider_cache["mistral"] = FakeProvider(
        ProviderConfig(name="mistral", base_url="http://x", api_key="k", models=[], rate_limits={}),
        error=ProviderError("rate limited", "429"),
    )
    router_mod._provider_cache["openrouter"] = FakeProvider(
        ProviderConfig(name="openrouter", base_url="http://x", api_key="k", models=[], rate_limits={}),
        response=ChatResponse(
            model="or-gpt-oss-120b",
            choices=[{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            provider="openrouter",
        ),
    )

    request = ChatRequest(
        model="mistral-codestral",          # auto tier -> gate passes
        messages=[Message(role="user", content="hi")],
        task_type="coding",
    )
    response = await chat_completions(request, _FakeRequest(_regular()))
    # JSONResponse on success (not a 403 error_response).
    assert response.status_code == 200


# --- TenantStore roundtrip -------------------------------------------------

@pytest.mark.asyncio
async def test_store_resolve_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "tenant.db"
    monkeypatch.setattr(
        "src.core.tenant.get_config",
        lambda: SimpleNamespace(database=SimpleNamespace(path=str(db))),
    )
    store = TenantStore()
    await store.init()
    await store.upsert_client(
        client_id="acme", plain_key="sk-acme-secret",
        plan="enterprise", allowed_tiers=["auto", "dedicated"],
        allowed_models=["gh-gpt-4.1"],
    )

    principal = await store.resolve("sk-acme-secret")
    assert principal is not None
    assert principal.client_id == "acme"
    assert principal.allowed_tiers == frozenset({"auto", "dedicated"})
    assert "gh-gpt-4.1" in principal.allowed_model_ids

    assert await store.resolve("wrong-key") is None     # unknown key

    await store.upsert_client(
        client_id="acme", plain_key="sk-acme-secret", enabled=False
    )
    assert await store.resolve("sk-acme-secret") is None  # disabled client


def test_hash_key_is_stable_and_not_plaintext():
    digest = hash_key("sk-secret")
    assert digest == hash_key("sk-secret")
    assert "sk-secret" not in digest
    assert len(digest) == 64
