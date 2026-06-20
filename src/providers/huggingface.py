"""HuggingFace Inference API provider (OpenAI-compatible)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class HuggingfaceProvider(OpenAICompatibleProvider):
    """Gateway provider for HuggingFace Inference API (https://huggingface.co)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config, provider_id="huggingface", health_model="meta-llama/llama-3.3-70b-instruct")
