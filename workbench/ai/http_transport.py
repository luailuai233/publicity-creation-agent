from __future__ import annotations

from typing import Any

import httpx
from pydantic import SecretStr

from workbench.ai.errors import (
    AIAuthenticationError,
    AINetworkError,
    AIRateLimitError,
    AIRequestError,
    AIResponseSchemaError,
)


class OpenAIHTTPTransport:
    def __init__(
        self,
        base_url: str,
        api_key: SecretStr | str,
        *,
        connect_timeout: float = 10,
        read_timeout: float = 120,
        write_timeout: float = 30,
        pool_timeout: float = 10,
        max_connections: int = 10,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        secret = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            timeout=httpx.Timeout(connect=connect_timeout, read=read_timeout, write=write_timeout, pool=pool_timeout),
            limits=httpx.Limits(max_connections=max_connections),
            transport=transport,
        )

    def post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            try:
                response = self.client.post("chat/completions", json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 0:
                    continue
                raise AINetworkError("AI service is temporarily unreachable") from exc
            if response.status_code in {401, 403}:
                raise AIAuthenticationError("AI service rejected the configured credentials")
            if response.status_code == 429:
                if attempt == 0:
                    continue
                raise AIRateLimitError("AI service rate limit exceeded")
            if response.status_code >= 500:
                if attempt == 0:
                    continue
                raise AINetworkError("AI service returned a temporary server error")
            if response.status_code >= 400:
                raise AIRequestError(f"AI service rejected the request with status {response.status_code}")
            try:
                return response.json()
            except ValueError as exc:
                raise AIResponseSchemaError("AI service returned invalid JSON") from exc
        raise AINetworkError()
