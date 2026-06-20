"""Reusable provider contract — the "template test" for any new model provider.

A new OpenAI-compatible provider gets full coverage by subclassing
:class:`OpenAICompatibleProviderContract`, setting three attributes, and
implementing :meth:`make_provider`. The inherited tests assert the four things
every provider must get right:

1. **Connectivity** — a 200 from the backend yields a unified ``ChatResponse``.
2. **Auth errors** — a 401 (and a missing key) raise ``ProviderError("401")``.
3. **Unreachable URL** — a transport failure raises a fallback-eligible error,
   never a raw ``httpx`` exception.
4. **Payload validation** — the body sent on the wire is valid OpenAI
   ``/chat/completions`` JSON with the resolved provider-side model id.

No network and no real API key are used: an ``httpx.MockTransport`` is injected
into the provider's client and a one-model registry is seeded in memory.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any, Callable

import httpx
import pytest

import src.core.registry as registry_module
from src.core.types import ChatRequest, ChatResponse, Message, ModelInfo, ProviderError
from src.providers.base import BaseProvider

_HandlerType = Callable[[httpx.Request], httpx.Response]


def make_model_info(provider_id: str, gateway_id: str, provider_model_id: str) -> ModelInfo:
    """Build a minimal but valid ``ModelInfo`` for contract tests."""
    return ModelInfo(
        id=gateway_id,
        display_name=gateway_id,
        provider_id=provider_id,
        provider_model_id=provider_model_id,
        strength="A",
        use_cases=["coding"],
        context_window=8192,
        max_output_tokens=2048,
        rate_limits={},
        added_at="2026-01-01",
        last_verified="2026-01-01",
    )


@contextlib.contextmanager
def seeded_registry(model: ModelInfo):
    """Temporarily install a registry singleton holding exactly one model."""
    previous = registry_module._registry
    registry = registry_module.Registry()
    registry._models = {model.id: model}
    registry_module._registry = registry
    try:
        yield
    finally:
        registry_module._registry = previous


def openai_success_payload(content: str = "pong") -> dict[str, Any]:
    """A canonical OpenAI ``/chat/completions`` success body."""
    return {
        "id": "chatcmpl-contract",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
    }


@pytest.mark.asyncio
class OpenAICompatibleProviderContract:
    """Inheritable contract. Subclass, set the three attributes, and implement
    :meth:`make_provider`. Do not add ``Test`` to this class name so pytest does
    not collect the abstract base itself."""

    provider_id: str
    gateway_model_id: str
    provider_model_id: str

    # ------------------------------------------------------------------ hooks
    def make_provider(self, *, api_key: str = "contract-test-key") -> BaseProvider:
        """Return the provider under test. Override in the subclass."""
        raise NotImplementedError

    # --------------------------------------------------------------- helpers
    def _model(self) -> ModelInfo:
        return make_model_info(self.provider_id, self.gateway_model_id, self.provider_model_id)

    def _request(self) -> ChatRequest:
        return ChatRequest(
            model=self.gateway_model_id,
            messages=[Message(role="user", content="ping")],
        )

    async def _chat(self, handler: _HandlerType, *, api_key: str = "contract-test-key") -> ChatResponse:
        provider = self.make_provider(api_key=api_key)
        provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            with seeded_registry(self._model()):
                return await provider.chat(self._request())
        finally:
            await provider.close()

    # ----------------------------------------------------------------- tests
    async def test_connectivity_returns_unified_response(self) -> None:
        """A backend 200 is translated into a unified ChatResponse."""

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=openai_success_payload("pong"))

        response = await self._chat(handler)

        assert isinstance(response, ChatResponse)
        assert response.provider == self.provider_id
        assert response.model == self.gateway_model_id
        assert response.choices[0].message["content"] == "pong"
        assert response.usage.total_tokens == 4

    async def test_payload_is_openai_chat_format(self) -> None:
        """The request sent on the wire is valid OpenAI /chat/completions JSON."""
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("Authorization")
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=openai_success_payload())

        await self._chat(handler)

        assert captured["url"].endswith("/chat/completions")
        assert captured["auth"] == "Bearer contract-test-key"
        body = captured["body"]
        # Model must be the PROVIDER-side id, not the gateway id.
        assert body["model"] == self.provider_model_id
        assert isinstance(body["messages"], list) and body["messages"]
        assert body["messages"][0] == {"role": "user", "content": "ping"}
        assert isinstance(body["temperature"], (int, float))
        assert isinstance(body["max_tokens"], int)
        assert isinstance(body["stream"], bool)

    async def test_invalid_api_key_raises_401(self) -> None:
        """A 401 from the backend surfaces as ProviderError with code '401'."""

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "invalid api key"})

        with pytest.raises(ProviderError) as exc_info:
            await self._chat(handler, api_key="wrong-key")
        assert exc_info.value.code == "401"

    async def test_missing_api_key_raises_before_call(self) -> None:
        """An empty key fails fast as a 401 without touching the network."""

        def handler(_request: httpx.Request) -> httpx.Response:  # pragma: no cover
            raise AssertionError("must not call the backend without a key")

        with pytest.raises(ProviderError) as exc_info:
            await self._chat(handler, api_key="")
        assert exc_info.value.code == "401"

    async def test_unreachable_url_raises_provider_error(self) -> None:
        """A transport failure becomes a fallback-eligible ProviderError, not a
        raw httpx error."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        with pytest.raises(ProviderError) as exc_info:
            await self._chat(handler)
        assert exc_info.value.code == "5xx"
