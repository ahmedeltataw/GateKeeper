"""OpenRouter provider implementation."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """Gateway provider for OpenRouter (https://openrouter.ai)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_id="openrouter",
            health_model="nvidia/nemotron-3-ultra-550b-a55b:free",
        )
