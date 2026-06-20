"""Tests for per-tenant usage tracking, quotas, and the usage views."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.api.routes import build_usage_view, chat_completions, usage_endpoint
from src.core import usage
from src.core.config_loader import get_config
from src.core.registry import get_registry
from src.core.tenant import OWNER, PLAN_DEFAULTS, Principal, TenantStore, quota_for
from src.core.types import ChatRequest, Message


class _FakeRequest:
    def __init__(self, principal: Principal) -> None:
        self.state = SimpleNamespace(principal=principal)
        self.headers: dict[str, str] = {}


def _client(**kw) -> Principal:
    base = dict(
        client_id="acme", plan="pro", allowed_tiers=frozenset({"auto"}),
        quota_requests=1000, quota_tokens=500_000,
    )
    base.update(kw)
    return Principal(**base)


@pytest.fixture(autouse=True)
def _reset_usage():
    usage.reset()
    usage.reset_store()
    yield
    usage.reset()
    usage.reset_store()


# --- counter store ---------------------------------------------------------

def test_record_and_get_client_usage():
    usage.record("acme", "or-gpt-oss-120b", tokens=100)
    usage.record("acme", "or-gpt-oss-120b", tokens=50)
    usage.record("acme", "gh-gpt-4.1", tokens=10)
    usage.record("other", "or-gpt-oss-120b", tokens=999)

    acme = usage.get_client_usage("acme")
    assert acme["or-gpt-oss-120b"] == {"requests": 2, "tokens": 150}
    assert acme["gh-gpt-4.1"] == {"requests": 1, "tokens": 10}
    assert "other" not in acme  # isolation between clients


@pytest.mark.asyncio
async def test_flush_then_reseed_roundtrip(tmp_path, monkeypatch):
    db = tmp_path / "usage.db"
    monkeypatch.setattr(
        "src.core.usage.get_config",
        lambda: SimpleNamespace(database=SimpleNamespace(path=str(db))),
    )
    await usage.init()
    usage.record("acme", "or-gpt-oss-120b", tokens=200)
    await usage.flush()

    usage.reset()  # simulate a process restart (memory gone, db intact)
    await usage.init()  # init reseeds the current period from disk

    restored = usage.get_client_usage("acme")
    assert restored["or-gpt-oss-120b"] == {"requests": 1, "tokens": 200}


# --- quota resolution ------------------------------------------------------

def test_quota_for_plan_default_and_override():
    assert quota_for("free") == PLAN_DEFAULTS["free"]
    # Override > 0 wins; 0 falls back to the plan default.
    merged = quota_for("free", {"requests": 999, "tokens": 0})
    assert merged["requests"] == 999
    assert merged["tokens"] == PLAN_DEFAULTS["free"]["tokens"]


def test_principal_limit_for_uses_model_cap_then_account():
    principal = _client(model_limits={"gh-gpt-4.1": {"requests": 5, "tokens": 7}})
    assert principal.limit_for("gh-gpt-4.1") == {"requests": 5, "tokens": 7}
    assert principal.limit_for("or-gpt-oss-120b") == {"requests": 1000, "tokens": 500_000}


# --- usage view ------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_usage_view_percent(loaded_registry):
    await get_registry()
    usage.record("acme", "or-gpt-oss-120b", tokens=250_000)  # 50% of 500k tokens
    principal = _client()

    view = await build_usage_view(principal)
    assert view["client_id"] == "acme"
    assert view["totals"]["tokens"] == 250_000
    assert view["percent"]["tokens"] == 50.0

    model = next(m for m in view["models"] if m["id"] == "or-gpt-oss-120b")
    assert model["name"]                       # display name resolved from registry
    assert model["percent"]["tokens"] == 50.0


@pytest.mark.asyncio
async def test_usage_endpoint_owner_unlimited(loaded_registry):
    await get_registry()
    usage.record("owner", "or-gpt-oss-120b", tokens=10)
    view = await usage_endpoint(_FakeRequest(OWNER))
    # Owner quota is 0 (unlimited) -> percent stays 0 even with usage.
    assert view["quota"]["tokens"] == 0
    assert view["percent"]["tokens"] == 0.0


# --- enforcement gate ------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_gate_blocks_when_quota_exceeded(loaded_registry):
    cfg = get_config()
    original = cfg.usage.enforce
    cfg.usage.enforce = True
    try:
        principal = _client(quota_requests=2, quota_tokens=0)
        usage.record("acme", "or-gpt-oss-120b", tokens=0)
        usage.record("acme", "or-gpt-oss-120b", tokens=0)  # now at the cap (2)

        request = ChatRequest(
            model="or-gpt-oss-120b", messages=[Message(role="user", content="hi")]
        )
        response = await chat_completions(request, _FakeRequest(principal))
        assert response.status_code == 429
    finally:
        cfg.usage.enforce = original


@pytest.mark.asyncio
async def test_owner_bypasses_enforcement(loaded_registry):
    cfg = get_config()
    original = cfg.usage.enforce
    cfg.usage.enforce = True
    try:
        # Owner has unlimited quota and is_owner -> gate must not 429 here. We
        # only assert the quota gate itself does not block (provider not mocked,
        # so a real call would fail later, but never with a 429 quota error).
        from src.api.routes import _quota_exceeded
        assert _quota_exceeded(OWNER) is None
    finally:
        cfg.usage.enforce = original


# --- tenant store quota persistence ---------------------------------------

@pytest.mark.asyncio
async def test_store_persists_quota_and_model_limits(tmp_path, monkeypatch):
    db = tmp_path / "tenant.db"
    monkeypatch.setattr(
        "src.core.tenant.get_config",
        lambda: SimpleNamespace(database=SimpleNamespace(path=str(db))),
    )
    store = TenantStore()
    await store.init()
    await store.upsert_client(
        client_id="acme", plain_key="sk-acme", plan="pro",
        quota_requests=1234, model_limits={"gh-gpt-4.1": {"tokens": 999}},
    )
    principal = await store.resolve("sk-acme")
    assert principal.quota_requests == 1234
    assert principal.quota_tokens == PLAN_DEFAULTS["pro"]["tokens"]  # 0 -> plan default
    assert principal.limit_for("gh-gpt-4.1")["tokens"] == 999

    principals = await store.list_principals()
    assert any(p.client_id == "acme" for p in principals)
