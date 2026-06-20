"""Mistral AI provider (OpenAI-compatible)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    """Gateway provider for Mistral AI (https://mistral.ai)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="mistral", health_model="codestral-latest")
