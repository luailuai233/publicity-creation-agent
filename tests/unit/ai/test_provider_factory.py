import pytest

from workbench.ai.factory import UnknownProviderError, create_ai_provider
from workbench.ai.mock_provider import MockAIProvider
from workbench.ai.openai_compatible_provider import OpenAICompatibleProvider
from workbench.settings import Settings


def test_factory_returns_offline_mock_provider_by_default() -> None:
    provider = create_ai_provider(Settings(mock_ai_delay_ms=17))

    assert isinstance(provider, MockAIProvider)
    assert provider.delay_ms == 17


def test_factory_builds_openai_compatible_provider_without_leaking_key() -> None:
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="super-secret-key", ai_model="example-model")
    provider = create_ai_provider(settings)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert "super-secret-key" not in repr(settings)


def test_factory_rejects_unknown_provider_name() -> None:
    with pytest.raises(UnknownProviderError, match="unsupported"):
        create_ai_provider(Settings(ai_provider="unsupported"))
