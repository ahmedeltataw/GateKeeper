"""Cerebras provider (OpenAI-compatible, unstable — use as fallback only)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class CerebrasProvider(OpenAICompatibleProvider):
    """Gateway provider for Cerebras (https://cerebras.ai)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="cerebras", health_model="gpt-oss-120b")
