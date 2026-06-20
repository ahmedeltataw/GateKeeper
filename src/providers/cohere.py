"""Cohere provider (OpenAI-compatible)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class CohereProvider(OpenAICompatibleProvider):
    """Gateway provider for Cohere (https://cohere.com)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="cohere", health_model="command-a-plus-05-2026")
