"""Zhipu AI provider (OpenAI-compatible)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class ZhipuProvider(OpenAICompatibleProvider):
    """Gateway provider for Zhipu AI (https://open.bigmodel.cn)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="zhipu", health_model="glm-4.7-flash")
