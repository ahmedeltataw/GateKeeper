"""Provider discovery and factory."""

from __future__ import annotations

from src.providers.aion import AionProvider
from src.providers.base import BaseProvider, ProviderConfig
from src.providers.cerebras import CerebrasProvider
from src.providers.cloudflare import CloudflareProvider
from src.providers.cohere import CohereProvider
from src.providers.gemini import GeminiProvider
from src.providers.github_models import GithubModelsProvider
from src.providers.groq import GroqProvider
from src.providers.huggingface import HuggingfaceProvider
from src.providers.mistral import MistralProvider
from src.providers.nvidia import NvidiaProvider
from src.providers.openrouter import OpenRouterProvider
from src.providers.zhipu import ZhipuProvider

_PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "openrouter": OpenRouterProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "github_models": GithubModelsProvider,
    "nvidia": NvidiaProvider,
    "cerebras": CerebrasProvider,
    "cloudflare": CloudflareProvider,
    "zhipu": ZhipuProvider,
    "huggingface": HuggingfaceProvider,
    "aion": AionProvider,
    "cohere": CohereProvider,
}


def create_provider(provider_id: str, config: ProviderConfig) -> BaseProvider:
    """Create a provider instance by id."""
    provider_class = _PROVIDER_CLASSES.get(provider_id)
    if provider_class is None:
        raise ValueError(f"Unknown provider: {provider_id}")
    return provider_class(config)


def list_provider_ids() -> list[str]:
    """Return all registered provider ids."""
    return list(_PROVIDER_CLASSES.keys())


def register_provider(provider_id: str, provider_class: type[BaseProvider]) -> None:
    """Register a new provider implementation (used when adding providers)."""
    _PROVIDER_CLASSES[provider_id] = provider_class
