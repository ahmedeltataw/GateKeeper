"""Groq provider (OpenAI-compatible)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Gateway provider for Groq (https://groq.com)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="groq", health_model="llama-3.3-70b-versatile")
