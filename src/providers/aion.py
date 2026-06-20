"""Aion Labs provider (OpenAI-compatible)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class AionProvider(OpenAICompatibleProvider):
    """Gateway provider for Aion Labs (https://aionlabs.ai)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="aion", health_model="aion-2.5")
