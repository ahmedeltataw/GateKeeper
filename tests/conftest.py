"""Shared fixtures for the gateway test suite."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.server import create_app
from src.core import cache, circuit, health, key_manager, rate_limiter
from src.core.registry import Registry, reset_registry
from src.core.router import reset_providers
from src.core.types import ChatRequest, ChatResponse, HealthStatus, ProviderError
from src.providers.base import BaseProvider, ProviderConfig

pytest_plugins = ("pytest_asyncio",)


class FakeProvider(BaseProvider):
    """Test double whose behaviour is controlled by the test."""

    def __init__(
        self,
        config: ProviderConfig,
        *,
        response: ChatResponse | None = None,
        error: ProviderError | None = None,
        stream_error: ProviderError | None = None,
        stream_content: str = "hi",
    ):
        super().__init__(config)
        self.response = response
        self.error = error
        self.stream_error = stream_error
        self.stream_content = stream_content
        self.calls: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        if self.error:
            raise self.error
        if self.response is None:
            raise ProviderError("no response configured", "5xx")
        return self.response

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        self.calls.append(request)
        # Pre-first-byte failure: raise so the streaming engine can fail over.
        if self.stream_error is not None:
            raise self.stream_error
        yield (
            'data: {"id":"1","object":"chat.completion.chunk","created":1,'
            f'"model":"m","choices":[{{"index":0,"delta":{{"role":"assistant",'
            f'"content":"{self.stream_content}"}},"finish_reason":null}}]}}\n\n'
        )
        yield 'data: [DONE]\n\n'

    async def list_models(self) -> list:
        return []

    async def check_health(self) -> HealthStatus:
        return HealthStatus.HEALTHY


@pytest_asyncio.fixture
async def loaded_registry():
    """Ensure the registry singleton is loaded for tests."""
    reset_registry()
    await reset_providers()
    cache._store.clear()
    await key_manager.init()
    registry = Registry()
    await registry.load()
    yield registry
    reset_registry()
    await reset_providers()
    cache._store.clear()


@pytest_asyncio.fixture
async def test_app():
    """Create a fresh FastAPI app for each async test."""
    reset_registry()
    await reset_providers()
    # Use a temporary in-memory key manager path.
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client
    reset_registry()
    await reset_providers()


@pytest.fixture
def provider_config() -> ProviderConfig:
    return ProviderConfig(
        name="fake",
        base_url="http://fake",
        api_key="fake-key",
        models=[],
        rate_limits={},
    )


@pytest.fixture
def sample_response() -> ChatResponse:
    return ChatResponse(
        model="codestral",
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello"},
                "finish_reason": "stop",
            }
        ],
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        provider="fake",
    )


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limiter():
    """Reset rate limiter buckets, provider health, and circuit state per test."""
    rate_limiter._buckets.clear()
    health.reset()
    circuit.reset_all()
    yield
    rate_limiter._buckets.clear()
    health.reset()
    circuit.reset_all()


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
