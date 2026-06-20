"""Tests for the 4-tier fallback engine."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from src.core import rate_limiter, router as router_mod
from src.core.fallback import stream_with_fallback, try_with_fallback
from src.core.registry import get_registry
from src.core.types import (
    AllRateLimitedError,
    ChatRequest,
    ChatResponse,
    Message,
    ProviderError,
)
from src.providers.base import ProviderConfig
from tests.conftest import FakeProvider


@pytest.fixture
def chat_request() -> ChatRequest:
    return ChatRequest(
        model="mistral-codestral",
        messages=[Message(role="user", content="hi")],
    )


@pytest.mark.asyncio
async def test_streaming_fails_over_before_first_byte(chat_request, loaded_registry):
    """A pre-stream 429 on the preferred provider must fail over silently, not
    leak an error chunk — the user receives the alternate provider's stream."""
    router_mod._provider_cache["mistral"] = FakeProvider(
        ProviderConfig(name="mistral", base_url="http://x", api_key="k", models=[], rate_limits={}),
        stream_error=ProviderError("rate limited", "429"),
    )
    router_mod._provider_cache["openrouter"] = FakeProvider(
        ProviderConfig(name="openrouter", base_url="http://x", api_key="k", models=[], rate_limits={}),
        stream_content="recovered",
    )

    chunks = [chunk async for chunk in stream_with_fallback(chat_request, "coding")]
    body = "".join(chunks)

    assert "recovered" in body
    assert '"error"' not in body
    assert "data: [DONE]" in body


@pytest.mark.asyncio
async def test_tier1_success_no_fallback(chat_request, loaded_registry):
    router_mod._provider_cache["mistral"] = FakeProvider(
        ProviderConfig(name="mistral", base_url="http://x", api_key="k", models=[], rate_limits={}),
        response=ChatResponse(
            model="codestral",
            choices=[{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            provider="mistral",
        ),
    )

    response = await try_with_fallback(chat_request, "coding")
    assert response.fallback_used is False
    assert response.original_model == "mistral-codestral"


@pytest.mark.asyncio
async def test_tier2_injects_context_handoff_on_429(chat_request, loaded_registry):
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

    response = await try_with_fallback(chat_request, "coding")
    assert response.fallback_used is True
    assert response.original_model == "mistral-codestral"
    assert "or-gpt-oss-120b" in response.fallback_chain


@pytest.mark.asyncio
async def test_401_permanently_disables_provider(chat_request, loaded_registry):
    router_mod._provider_cache["mistral"] = FakeProvider(
        ProviderConfig(name="mistral", base_url="http://x", api_key="k", models=[], rate_limits={}),
        error=ProviderError("bad key", "401"),
    )
    router_mod._provider_cache["openrouter"] = FakeProvider(
        ProviderConfig(name="openrouter", base_url="http://x", api_key="k", models=[], rate_limits={}),
        response=ChatResponse(
            model="nemotron-3-ultra",
            choices=[{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            provider="openrouter",
        ),
    )

    await try_with_fallback(chat_request, "coding")
    assert await rate_limiter.allow("mistral") is False


@pytest.mark.asyncio
async def test_exhaustion_when_all_providers_rate_limited_raises_429(chat_request, loaded_registry):
    registry = await get_registry()
    # Limit the active model set to models whose providers we mock.
    active_models = [
        m for m in registry.all_models()
        if m.provider_id in {"mistral", "openrouter", "gemini"}
    ]
    for pid in {"mistral", "openrouter", "gemini"}:
        router_mod._provider_cache[pid] = FakeProvider(
            ProviderConfig(name=pid, base_url="http://x", api_key="k", models=[], rate_limits={}),
            error=ProviderError("rate limited", "429"),
        )

    with pytest.raises(AllRateLimitedError):
        with patch.object(registry, "get_active", return_value=active_models):
            await try_with_fallback(chat_request, "coding")
