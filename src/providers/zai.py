"""Z.ai provider (GLM models, OpenAI-compatible).

Z.ai (https://z.ai) exposes Zhipu's GLM family behind an OpenAI-standard
``/chat/completions`` endpoint, so it reuses the generic
:class:`~src.providers.openai_compatible.OpenAICompatibleProvider` wholesale and
only declares its plugin :class:`~src.providers.spec.ProviderSpec`.

This module is the reference example for the "add a provider" guide
(``docs/ADDING_A_PROVIDER.md``): a standard OpenAI-compatible provider needs
nothing more than the spec below.
"""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.spec import ProviderSpec, register_spec

_PROVIDER_ID = "zai"
# Permanently-free flash model; used only for health probes. (Migrated from the
# removed `zhipu` provider, which probed the same endpoint with this model.)
_HEALTH_MODEL = "glm-4.7-flash"


class ZaiProvider(OpenAICompatibleProvider):
    """Gateway provider for Z.ai's GLM API."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, provider_id=_PROVIDER_ID, health_model=_HEALTH_MODEL)


# Declarative registration — picked up by the factory, key bootstrap, and the
# provider listing without touching any other file.
SPEC = register_spec(
    ProviderSpec(
        id=_PROVIDER_ID,
        base_url="https://api.z.ai/api/paas/v4",
        env_var="ZAI_API_KEY",
        health_model=_HEALTH_MODEL,
        provider_class=ZaiProvider,
    )
)
