"""Provider abstraction shared by all provider implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from src.core.types import ChatRequest, ChatResponse, HealthStatus, ModelInfo


@dataclass
class ProviderConfig:
    """Runtime configuration for a single provider."""

    name: str
    base_url: str
    api_key: str
    models: list[str]
    rate_limits: dict[str, Any]


class BaseProvider(ABC):
    """Abstract base that every provider implementation must satisfy."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        # connect=10s: a dead/unreachable provider fails fast so fallback moves
        # on quickly. read=60s still allows legitimately slow generations.
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0)
        )

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat request and return a unified OpenAI-format response."""
        raise NotImplementedError

    async def chat_stream(self, request: ChatRequest):
        """Yield SSE ``data: ...`` lines for a streaming chat request.

        Default implementation raises ``NotImplementedError``; providers that
        support streaming must override this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support streaming"
        )

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Return the models this provider supports."""
        raise NotImplementedError

    @abstractmethod
    async def check_health(self) -> HealthStatus:
        """Return the current health status of this provider."""
        raise NotImplementedError

    async def close(self) -> None:
        await self.client.aclose()


def build_openai_envelope(
    model: str,
    content: str | None,
    provider: str,
    usage: dict[str, int] | None = None,
    finish_reason: str = "stop",
) -> ChatResponse:
    """Build a standard OpenAI-format ``ChatResponse``.

    Providers that already receive an OpenAI-compatible payload can reuse this
    helper after extracting the generated text.
    """
    usage = usage or {}
    return ChatResponse(
        model=model,
        choices=[
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        usage={
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get(
                "total_tokens",
                usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
            ),
        },
        provider=provider,
    )
