import httpx
import pytest

from workbench.ai.errors import AIAuthenticationError, AINetworkError, AIRateLimitError
from workbench.ai.http_transport import OpenAIHTTPTransport


def test_transport_retries_one_temporary_server_error_then_succeeds() -> None:
    attempts = 0
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(503 if attempts == 1 else 200, json={"ok": True})
    transport = OpenAIHTTPTransport("https://example.test/v1", "secret", transport=httpx.MockTransport(handler))
    assert transport.post_chat({"model": "test"}) == {"ok": True}
    assert attempts == 2


def test_transport_does_not_retry_authentication_and_never_leaks_key() -> None:
    transport = OpenAIHTTPTransport("https://example.test/v1", "super-secret", transport=httpx.MockTransport(lambda request: httpx.Response(401)))
    with pytest.raises(AIAuthenticationError) as caught:
        transport.post_chat({})
    assert "super-secret" not in str(caught.value)


def test_transport_maps_repeated_network_failure() -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")
    transport = OpenAIHTTPTransport("https://example.test/v1", "secret", transport=httpx.MockTransport(fail))
    with pytest.raises(AINetworkError):
        transport.post_chat({})


def test_transport_retries_rate_limit_once_then_succeeds() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429 if attempts == 1 else 200, json={"ok": True})

    transport = OpenAIHTTPTransport("https://example.test/v1", "secret", transport=httpx.MockTransport(handler))
    assert transport.post_chat({}) == {"ok": True}
    assert attempts == 2


def test_transport_stops_after_two_rate_limit_or_server_failures() -> None:
    for status, error_type in ((429, AIRateLimitError), (503, AINetworkError)):
        attempts = 0

        def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(status)

        transport = OpenAIHTTPTransport("https://example.test/v1", "secret", transport=httpx.MockTransport(handler))
        with pytest.raises(error_type):
            transport.post_chat({})
        assert attempts == 2
