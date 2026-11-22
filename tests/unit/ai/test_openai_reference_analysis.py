import json
import httpx
import pytest

from workbench.ai.errors import AIResponseSchemaError
from workbench.ai.http_transport import OpenAIHTTPTransport
from workbench.ai.openai_compatible_provider import OpenAICompatibleProvider
from workbench.settings import Settings


def test_reference_analysis_is_structured_and_does_not_send_activity_facts() -> None:
    requests = []
    result = {"hook":"现场细节","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["细节开场"],"avoid":["照搬原句"]}
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(result, ensure_ascii=False)}}]})
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))
    envelope = provider.analyze_reference("用户案例正文", "ref-1")
    assert envelope.source_ids == ["ref-1"]
    assert envelope.result.hook == "现场细节"
    assert "activity_facts" not in json.dumps(requests, ensure_ascii=False)


def test_reference_analysis_repairs_structure_once_and_then_rejects() -> None:
    valid = {"hook":"现场细节","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["方法"],"avoid":["照搬"]}

    def build_provider(payloads):
        remaining = list(payloads)
        def handler(_request):
            return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(remaining.pop(0), ensure_ascii=False)}}]})
        settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
        return OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))

    assert build_provider([{}, valid]).analyze_reference("案例", "ref-1").retries == 1
    with pytest.raises(AIResponseSchemaError):
        build_provider([{}, {}]).analyze_reference("案例", "ref-1")


def test_reference_analysis_rejects_model_supplied_source_id() -> None:
    invalid = {"source_id":"other","hook":"现场细节","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["方法"],"avoid":["照搬"]}
    def handler(_request):
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(invalid, ensure_ascii=False)}}]})
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))
    with pytest.raises(AIResponseSchemaError):
        provider.analyze_reference("案例", "ref-1")


def test_reference_analysis_explicitly_requests_json_output() -> None:
    requests = []
    valid = {"hook":"现场细节","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["方法"],"avoid":["照搬"]}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(valid, ensure_ascii=False)}}]})

    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))

    provider.analyze_reference("案例", "ref-1")

    assert "JSON" in requests[0]["messages"][0]["content"]


def test_reference_analysis_retries_without_response_format_when_endpoint_rejects_it() -> None:
    requests = []
    valid = {"hook":"现场细节","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["方法"],"avoid":["照搬"]}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if "response_format" in payload:
            return httpx.Response(400, json={"error": {"message": "response_format is not supported"}})
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(valid, ensure_ascii=False)}}]})

    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))

    result = provider.analyze_reference("案例", "ref-1")

    assert result.status == "DONE"
    assert len(requests) == 2
    assert requests[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in requests[1]


def test_reference_analysis_supplies_deepseek_with_an_exact_json_example_and_output_budget() -> None:
    requests = []
    valid = {"hook":"现场细节","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["方法"],"avoid":["照搬"]}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(valid, ensure_ascii=False)}}]})

    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://api.deepseek.com", ai_api_key="secret", ai_model="deepseek-flash")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))

    provider.analyze_reference("案例", "ref-1")

    system_prompt = requests[0]["messages"][0]["content"]
    assert '"hook"' in system_prompt
    assert '"emotion"' in system_prompt
    assert '"transferable"' in system_prompt
    assert requests[0]["max_tokens"] == 4096


def test_reference_analysis_repair_includes_the_invalid_output_and_validation_details() -> None:
    requests = []
    invalid = {"hook": "只有钩子"}
    valid = {"hook":"现场细节","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["方法"],"avoid":["照搬"]}
    responses = [invalid, valid]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        content = json.dumps(responses.pop(0), ensure_ascii=False)
        return httpx.Response(200, json={"choices":[{"message":{"content":content}}]})

    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://api.deepseek.com", ai_api_key="secret", ai_model="deepseek-flash")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))

    result = provider.analyze_reference("案例", "ref-1")

    repair_messages = requests[1]["messages"]
    assert result.result.emotion == "克制温暖"
    assert repair_messages[-2] == {"role": "assistant", "content": json.dumps(invalid, ensure_ascii=False)}
    assert "emotion" in repair_messages[-1]["content"]
