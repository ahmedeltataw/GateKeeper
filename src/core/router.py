"""Model → provider routing and provider lifecycle."""

from __future__ import annotations

from src.core import key_manager
from src.core.config_loader import get_config
from src.core.registry import get_registry, get_registry_sync
from src.core.types import ModelInfo, ProviderError
from src.providers import create_provider
from src.providers.base import BaseProvider, ProviderConfig

_provider_cache: dict[str, BaseProvider] = {}


async def _provider_key(provider_id: str) -> str:
    """Return the decrypted API key for a provider from the key manager."""
    return await key_manager.get_key(provider_id)


async def _provider_config(provider_id: str) -> ProviderConfig:
    """Build a ProviderConfig from the global configuration."""
    app_config = get_config()
    provider_cfg = app_config.providers.get(provider_id)
    if provider_cfg is None:
        raise ValueError(f"Provider '{provider_id}' not configured")

    registry = get_registry_sync()
    models = [m.id for m in registry.all_models() if m.provider_id == provider_id]

    return ProviderConfig(
        name=provider_id,
        base_url=provider_cfg.base_url,
        api_key=await _provider_key(provider_id),
        models=models,
        rate_limits={},
    )


async def get_provider(provider_id: str) -> BaseProvider:
    """Return a cached provider instance for the given provider id."""
    if provider_id not in _provider_cache:
        _provider_cache[provider_id] = create_provider(
            provider_id, await _provider_config(provider_id)
        )
    return _provider_cache[provider_id]


async def invalidate_provider(provider_id: str) -> None:
    """Drop a cached provider instance (e.g. after a bad-key 401).

    The next call to ``get_provider`` rebuilds it, re-reading the key so a fixed
    key is picked up without a restart.
    """
    provider = _provider_cache.pop(provider_id, None)
    if provider is not None:
        try:
            await provider.close()
        except Exception:
            pass


async def reset_providers() -> None:
    """Close and clear all cached provider instances."""
    global _provider_cache
    for provider in _provider_cache.values():
        try:
            await provider.close()
        except Exception:
            pass
    _provider_cache = {}


async def resolve_model(model_id: str) -> ModelInfo:
    """Look up a gateway model id in the registry."""
    registry = await get_registry()
    model = registry.get(model_id)
    if model is None:
        available = ", ".join(sorted(m.id for m in registry.get_active()))
        raise ProviderError(
            f"Model '{model_id}' not found. Available models: {available}", "404"
        )
    return model


async def route_to_provider(model_id: str) -> tuple[BaseProvider, ModelInfo]:
    """Resolve a model and return its provider plus model metadata."""
    model = await resolve_model(model_id)
    provider = await get_provider(model.provider_id)
    return provider, model
