"""NVIDIA NIM provider (partial OpenAI-compatible, evaluation-only ToS)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class NvidiaProvider(OpenAICompatibleProvider):
    """Gateway provider for NVIDIA NIM (https://build.nvidia.com).

    Note: NVIDIA's free tier is evaluation-only / non-commercial.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="nvidia", health_model="nvidia/nemotron-3-ultra")
