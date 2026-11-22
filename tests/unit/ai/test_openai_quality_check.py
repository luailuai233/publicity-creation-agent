import json
import httpx
import pytest

from workbench.ai.errors import AIResponseSchemaError
from workbench.ai.http_transport import OpenAIHTTPTransport
from workbench.ai.openai_compatible_provider import OpenAICompatibleProvider
from workbench.settings import Settings


def test_quality_check_rejects_unknown_issue_type() -> None:
    payload = {"issues":[{"type":"INTERNAL_REASONING","severity":"HIGH","block_id":"b1","message":"bad"}]}
    def handler(_request):
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(payload)}}]})
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))
    with pytest.raises(AIResponseSchemaError):
        provider.check_quality("正文", [{"id":"f1"}], [])


def test_quality_check_accepts_only_supported_severity() -> None:
    payload = {"issues":[{"type":"TONE_RISK","severity":"CRITICAL","block_id":"b1","message":"bad"}]}
    def handler(_request):
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(payload)}}]})
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))
    with pytest.raises(AIResponseSchemaError):
        provider.check_quality("正文", [{"id":"f1"}], [])
