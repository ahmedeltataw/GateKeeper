"""Z.ai provider tests.

Demonstrates the "template test" workflow: the connectivity / auth / unreachable
/ payload checks are inherited wholesale from
:class:`OpenAICompatibleProviderContract`; this file only declares the provider
specifics and adds plugin-registration assertions.
"""

from __future__ import annotations

import pytest

from src.providers import create_provider, list_provider_ids, provider_env_vars
from src.providers.base import BaseProvider, ProviderConfig
from src.providers.spec import get_spec
from src.providers.zai import ZaiProvider
from tests.provider_contract import OpenAICompatibleProviderContract


class TestZaiProviderContract(OpenAICompatibleProviderContract):
    """Run the shared provider contract against Z.ai."""

    provider_id = "zai"
    gateway_model_id = "glm-4.6"
    provider_model_id = "glm-4.6"

    def make_provider(self, *, api_key: str = "contract-test-key") -> BaseProvider:
        return ZaiProvider(
            ProviderConfig(
                name="zai",
                base_url="https://api.z.ai/api/paas/v4",
                api_key=api_key,
                models=[self.gateway_model_id],
                rate_limits={},
            )
        )


def test_zai_spec_is_registered() -> None:
    """The plugin spec is discoverable and declares the right endpoint + key."""
    spec = get_spec("zai")
    assert spec is not None
    assert spec.base_url == "https://api.z.ai/api/paas/v4"
    assert spec.env_var == "ZAI_API_KEY"
    assert spec.provider_class is ZaiProvider


def test_zai_is_listed_and_key_bootstrappable() -> None:
    """The provider shows up in discovery and the key-import map."""
    assert "zai" in list_provider_ids()
    assert provider_env_vars().get("zai") == "ZAI_API_KEY"


def test_factory_builds_zai_from_spec() -> None:
    """The id→instance factory resolves 'zai' via the spec registry."""
    provider = create_provider(
        "zai",
        ProviderConfig(
            name="zai",
            base_url="https://api.z.ai/api/paas/v4",
            api_key="k",
            models=[],
            rate_limits={},
        ),
    )
    assert isinstance(provider, ZaiProvider)
    assert provider.provider_id == "zai"
