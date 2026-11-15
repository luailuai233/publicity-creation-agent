from workbench.ai.mock_provider import MockAIProvider
from workbench.ai.provider import AIProvider
from workbench.settings import Settings


class ProviderNotInstalledError(RuntimeError):
    pass


class UnknownProviderError(ValueError):
    pass


def create_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "mock":
        return MockAIProvider(delay_ms=settings.mock_ai_delay_ms)
    if settings.ai_provider == "openai_compatible":
        raise ProviderNotInstalledError(
            "当前版本未内置真实网络 Provider；请按 README 的接口契约实现 OpenAICompatibleProvider 后再启用。"
        )
    raise UnknownProviderError(settings.ai_provider)
