"""Declarative provider plugin registry.

Adding a provider should be *declarative*: state its id, endpoint, key env var
and (optionally) a custom class, then register it. The factory, the env-var
key import, and ``list_provider_ids`` all read from this single registry, so a
new provider no longer requires editing several hand-maintained dicts.

A provider that speaks the OpenAI ``/chat/completions`` standard needs **no**
custom class at all — a bare :class:`ProviderSpec` is enough and
:meth:`ProviderSpec.build` constructs a generic
:class:`~src.providers.openai_compatible.OpenAICompatibleProvider` for it.
Providers with a non-standard wire format (e.g. Gemini, Cohere) set
``provider_class`` to their own :class:`~src.providers.base.BaseProvider`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Mapping

from src.providers.base import BaseProvider, ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider

_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True)
class ProviderSpec:
    """Everything the gateway needs to know to wire up one provider.

    Attributes:
        id: Stable provider id used in the registry, config, and key storage.
        base_url: Default API base (the source of truth is ``config.yaml``; this
            documents the endpoint and is handy for tests/tooling).
        env_var: Environment variable the API key is bootstrapped from.
        health_model: Provider-side model id used for health probes (OpenAI-
            compatible providers only). ``None`` falls back to the first model.
        extra_headers: Static headers added to every request (OpenAI-compatible).
        provider_class: Custom ``BaseProvider`` subclass for non-standard wire
            formats. ``None`` => build a generic OpenAI-compatible provider.
    """

    id: str
    base_url: str
    env_var: str
    health_model: str | None = None
    extra_headers: Mapping[str, str] = field(default_factory=dict)
    provider_class: type[BaseProvider] | None = None

    def __post_init__(self) -> None:
        if not _ID_PATTERN.match(self.id):
            raise ValueError(f"Invalid provider id '{self.id}' (use a-z0-9_)")

    def build(self, config: ProviderConfig) -> BaseProvider:
        """Instantiate the provider for a resolved runtime config."""
        if self.provider_class is not None:
            return self.provider_class(config)
        return OpenAICompatibleProvider(
            config,
            provider_id=self.id,
            health_model=self.health_model,
            extra_headers=dict(self.extra_headers),
        )


_SPECS: dict[str, ProviderSpec] = {}


def register_spec(spec: ProviderSpec) -> ProviderSpec:
    """Register a provider spec. Idempotent for identical re-imports; rejects
    a different spec reusing an existing id (catches copy-paste mistakes)."""
    existing = _SPECS.get(spec.id)
    if existing is not None and existing != spec:
        raise ValueError(f"Provider id '{spec.id}' is already registered")
    _SPECS[spec.id] = spec
    return spec


def get_spec(provider_id: str) -> ProviderSpec | None:
    return _SPECS.get(provider_id)


def all_specs() -> list[ProviderSpec]:
    return list(_SPECS.values())


def spec_env_vars() -> dict[str, str]:
    """Map every registered provider id to the env var holding its key."""
    return {spec.id: spec.env_var for spec in _SPECS.values()}
