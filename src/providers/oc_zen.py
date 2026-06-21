"""OpenCode Zen provider (OpenAI-compatible).

OpenCode Zen (https://opencode.ai/docs/zen/) exposes a free tier of modern
reasoning/chat models behind an OpenAI-standard ``/chat/completions`` endpoint,
so it reuses the generic
:class:`~src.providers.openai_compatible.OpenAICompatibleProvider` wholesale and
only declares its plugin :class:`~src.providers.spec.ProviderSpec`.

Free tier requires a (free) OpenCode account; no payment card. See
``docs/ROADMAP_AND_IMPROVEMENTS.md`` §1.2 for the catalogued models.
"""

from __future__ import annotations

from src.providers.base import ProviderConfig
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.spec import ProviderSpec, register_spec

_PROVIDER_ID = "oc_zen"
# Permanently-free flash model; used only for health probes.
_HEALTH_MODEL = "deepseek-v4-flash-free"


class OcZenProvider(OpenAICompatibleProvider):
    """Gateway provider for the OpenCode Zen API."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config, provider_id=_PROVIDER_ID, health_model=_HEALTH_MODEL)


# Declarative registration — picked up by the factory, key bootstrap, and the
# provider listing without touching any other file.
SPEC = register_spec(
    ProviderSpec(
        id=_PROVIDER_ID,
        base_url="https://opencode.ai/v1",
        env_var="OC_ZEN_API_KEY",
        health_model=_HEALTH_MODEL,
        provider_class=OcZenProvider,
    )
)
