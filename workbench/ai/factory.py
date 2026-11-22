from workbench.ai.mock_provider import MockAIProvider
from workbench.ai.openai_compatible_provider import OpenAICompatibleProvider
from workbench.ai.provider import AIProvider
from workbench.settings import Settings


class UnknownProviderError(ValueError):
    pass


def create_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "mock":
        return MockAIProvider(delay_ms=settings.mock_ai_delay_ms)
    if settings.ai_provider == "openai_compatible":
        return OpenAICompatibleProvider(settings)
    raise UnknownProviderError(settings.ai_provider)
