class AIProviderError(RuntimeError):
    code = "AI_PROVIDER_ERROR"

    def __init__(self, message: str = "AI provider request failed") -> None:
        super().__init__(message)


class AIAuthenticationError(AIProviderError):
    code = "AI_AUTHENTICATION_ERROR"


class AIRateLimitError(AIProviderError):
    code = "AI_RATE_LIMIT_ERROR"


class AINetworkError(AIProviderError):
    code = "AI_NETWORK_ERROR"


class AIResponseSchemaError(AIProviderError):
    code = "AI_RESPONSE_SCHEMA_ERROR"


class AIContentError(AIProviderError):
    code = "AI_CONTENT_ERROR"


class AIRequestError(AIProviderError):
    code = "AI_REQUEST_ERROR"
