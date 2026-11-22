import json
import httpx
import pytest

from workbench.ai.errors import AIResponseSchemaError
from workbench.ai.http_transport import OpenAIHTTPTransport
from workbench.ai.openai_compatible_provider import OpenAICompatibleProvider
from workbench.settings import Settings


def provider_with_responses(*payloads):
    remaining = list(payloads)
    def handler(_request):
        payload = remaining.pop(0)
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(payload, ensure_ascii=False)}}]})
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    return OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))


def test_outline_has_one_editable_title_and_draft_uses_known_fact_ids() -> None:
    provider = provider_with_responses({"titles":["推荐标题"],"outline":["开头","正文"],"recommended_title_index":0}, {"content":"正文","cited_fact_ids":["f1"]})
    assert provider.generate_outline({"name":"策略"}, [{"id":"f1"}]).result.titles == ["推荐标题"]
    assert provider.generate_draft("推荐标题", ["开头"], {"name":"策略"}, [{"id":"f1"}]).result.cited_fact_ids == ["f1"]


def test_draft_rejects_unknown_fact_reference() -> None:
    with pytest.raises(AIResponseSchemaError):
        provider_with_responses({"content":"正文","cited_fact_ids":["unknown"]}).generate_draft("标题", ["正文"], {}, [{"id":"f1"}])


def test_outline_rejects_multiple_titles_and_internal_reasoning_fields() -> None:
    with pytest.raises(AIResponseSchemaError):
        provider_with_responses(
            {"titles":["一","二"],"outline":["正文"],"recommended_title_index":0},
            {"titles":["一","二"],"outline":["正文"],"recommended_title_index":0},
        ).generate_outline({}, [{"id":"f1"}])
    invalid = {"titles":["标题"],"outline":["正文"],"recommended_title_index":0,"internal_reasoning":"hidden"}
    with pytest.raises(AIResponseSchemaError):
        provider_with_responses(invalid, invalid).generate_outline({}, [{"id":"f1"}])
