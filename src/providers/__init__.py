"""Provider discovery and factory.

Two registration paths coexist:

* **Plugin specs** (preferred, see ``src/providers/spec.py``) — a provider
  module declares a :class:`~src.providers.spec.ProviderSpec` and calls
  ``register_spec``. Importing this package imports those modules, so the spec
  is available to the factory, the key bootstrap, and ``list_provider_ids``.
* **Legacy classes** — the original hand-maintained id→class map below. Kept for
  the providers not yet migrated to specs; specs take precedence on id clash.

To add a new OpenAI-compatible provider, prefer the spec path: no edit here.
"""

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
from src.providers.spec import all_specs, get_spec, register_spec, spec_env_vars

# Importing a provider module runs its register_spec() at import time. List every
# spec-based provider module here so the registry is populated on package import.
from src.providers import zai  # noqa: F401  (registers the "zai" spec)
from src.providers import oc_zen  # noqa: F401  (registers the "oc_zen" spec)

_LEGACY_CLASSES: dict[str, type[BaseProvider]] = {
    "openrouter": OpenRouterProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "github_models": GithubModelsProvider,
    "nvidia": NvidiaProvider,
    "cerebras": CerebrasProvider,
    "cloudflare": CloudflareProvider,
    "huggingface": HuggingfaceProvider,
    "aion": AionProvider,
    "cohere": CohereProvider,
}


def create_provider(provider_id: str, config: ProviderConfig) -> BaseProvider:
    """Create a provider instance by id (spec registry first, then legacy)."""
    spec = get_spec(provider_id)
    if spec is not None:
        return spec.build(config)

    provider_class = _LEGACY_CLASSES.get(provider_id)
    if provider_class is None:
        raise ValueError(f"Unknown provider: {provider_id}")
    return provider_class(config)


def list_provider_ids() -> list[str]:
    """Return all registered provider ids (specs + legacy), de-duplicated."""
    return sorted({*_LEGACY_CLASSES, *(spec.id for spec in all_specs())})


def provider_env_vars() -> dict[str, str]:
    """Map spec-registered provider ids to the env var holding their API key."""
    return spec_env_vars()


def register_provider(provider_id: str, provider_class: type[BaseProvider]) -> None:
    """Register a legacy provider class at runtime (back-compat shim)."""
    _LEGACY_CLASSES[provider_id] = provider_class


__all__ = [
    "BaseProvider",
    "ProviderConfig",
    "create_provider",
    "list_provider_ids",
    "provider_env_vars",
    "register_provider",
    "register_spec",
]
