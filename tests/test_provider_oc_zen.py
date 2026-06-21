"""OpenCode Zen provider tests.

Mirrors ``test_provider_zai.py``: connectivity / auth / unreachable / payload
checks are inherited from :class:`OpenAICompatibleProviderContract`; this file
declares the provider specifics and the plugin-registration assertions.
"""

from __future__ import annotations

from src.providers import create_provider, list_provider_ids, provider_env_vars
from src.providers.base import BaseProvider, ProviderConfig
from src.providers.oc_zen import OcZenProvider
from src.providers.spec import get_spec
from tests.provider_contract import OpenAICompatibleProviderContract

_BASE_URL = "https://opencode.ai/v1"


class TestOcZenProviderContract(OpenAICompatibleProviderContract):
    """Run the shared provider contract against OpenCode Zen."""

    provider_id = "oc_zen"
    gateway_model_id = "oczen-deepseek-v4-flash"
    provider_model_id = "deepseek-v4-flash-free"

    def make_provider(self, *, api_key: str = "contract-test-key") -> BaseProvider:
        return OcZenProvider(
            ProviderConfig(
                name="oc_zen",
                base_url=_BASE_URL,
                api_key=api_key,
                models=[self.gateway_model_id],
                rate_limits={},
            )
        )


def test_oc_zen_spec_is_registered() -> None:
    """The plugin spec is discoverable and declares the right endpoint + key."""
    spec = get_spec("oc_zen")
    assert spec is not None
    assert spec.base_url == _BASE_URL
    assert spec.env_var == "OC_ZEN_API_KEY"
    assert spec.provider_class is OcZenProvider


def test_oc_zen_is_listed_and_key_bootstrappable() -> None:
    """The provider shows up in discovery and the key-import map."""
    assert "oc_zen" in list_provider_ids()
    assert provider_env_vars().get("oc_zen") == "OC_ZEN_API_KEY"


def test_factory_builds_oc_zen_from_spec() -> None:
    """The id→instance factory resolves 'oc_zen' via the spec registry."""
    provider = create_provider(
        "oc_zen",
        ProviderConfig(
            name="oc_zen",
            base_url=_BASE_URL,
            api_key="k",
            models=[],
            rate_limits={},
        ),
    )
    assert isinstance(provider, OcZenProvider)
    assert provider.provider_id == "oc_zen"
