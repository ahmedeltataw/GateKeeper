"""GitHub Models provider (OpenAI-compatible)."""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider


class GithubModelsProvider(OpenAICompatibleProvider):
    """Gateway provider for GitHub Models (https://github.com/marketplace/models)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_id="github_models",
            health_model="openai/gpt-4o",
            extra_headers={"X-GitHub-Api-Version": "2022-11-28"},
        )
