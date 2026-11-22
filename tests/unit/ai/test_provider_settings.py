import pytest
from pydantic import ValidationError

from workbench.settings import Settings


def test_mock_provider_needs_no_credentials_and_secrets_are_masked() -> None:
    settings = Settings(ai_api_key="super-secret")
    assert settings.ai_provider == "mock"
    assert "super-secret" not in repr(settings)


@pytest.mark.parametrize("missing", ["ai_base_url", "ai_api_key", "ai_model"])
def test_real_provider_rejects_each_missing_required_setting(missing: str) -> None:
    values = {"ai_provider": "openai_compatible", "ai_base_url": "https://example.test/v1", "ai_api_key": "secret", "ai_model": "model"}
    values[missing] = None
    with pytest.raises(ValidationError):
        Settings(**values)


def test_real_provider_exposes_four_positive_timeouts() -> None:
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    assert (settings.ai_connect_timeout_seconds, settings.ai_read_timeout_seconds, settings.ai_write_timeout_seconds, settings.ai_pool_timeout_seconds) == (10, 120, 30, 10)
