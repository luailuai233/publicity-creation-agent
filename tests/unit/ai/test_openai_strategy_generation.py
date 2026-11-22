import json
import httpx
import pytest

from workbench.ai.errors import AIResponseSchemaError
from workbench.ai.http_transport import OpenAIHTTPTransport
from workbench.ai.openai_compatible_provider import OpenAICompatibleProvider
from workbench.settings import Settings


def _provider(payload):
    def handler(_request):
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(payload, ensure_ascii=False)}}]})
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://example.test/v1", ai_api_key="secret", ai_model="model")
    return OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))


def test_strategy_generation_accepts_exactly_three_different_strategies() -> None:
    strategies = [{"name":f"策略{i}","angle":f"角度{i}","opening":f"开头{i}","structure":f"结构{i}","fact_ids":[f"f{i}"],"method_summary":"细节开场","risk":"不扩大事实"} for i in range(1,4)]
    envelope = _provider({"strategies":strategies,"recommended_index":0}).generate_strategies([{"id":"f1"},{"id":"f2"},{"id":"f3"}], ["细节开场"], "活动")
    assert len(envelope.result.strategies) == 3


def test_strategy_generation_rejects_unknown_fact_id() -> None:
    strategies = [{"name":f"策略{i}","angle":f"角度{i}","opening":f"开头{i}","structure":f"结构{i}","fact_ids":["unknown"],"method_summary":"细节开场","risk":"风险"} for i in range(1,4)]
    with pytest.raises(AIResponseSchemaError):
        _provider({"strategies":strategies,"recommended_index":0}).generate_strategies([{"id":"f1"}], ["细节开场"], "活动")


def test_strategy_generation_rejects_wrong_count_missing_method_and_duplicates() -> None:
    valid = [{"name":f"策略{i}","angle":f"角度{i}","opening":f"开头{i}","structure":f"结构{i}","fact_ids":[f"f{i}"],"method_summary":"细节开场","risk":"风险"} for i in range(1,4)]
    cases = [
        valid[:2],
        [{**item, "method_summary": ""} for item in valid],
        [{**item, "name": "相同", "opening": "相同", "structure": "相同", "fact_ids": ["f1"]} for item in valid],
    ]
    for strategies in cases:
        with pytest.raises(AIResponseSchemaError):
            _provider({"strategies": strategies, "recommended_index": 0}).generate_strategies(
                [{"id":"f1"},{"id":"f2"},{"id":"f3"}], ["细节开场"], "活动"
            )


def test_strategy_generation_prompt_contains_an_exact_three_strategy_json_example() -> None:
    requests = []
    strategies = [
        {
            "name": f"策略{i}",
            "protagonist": f"主角{i}",
            "angle": f"角度{i}",
            "opening": f"开头{i}",
            "structure": f"结构{i}",
            "fact_ids": [f"f{i}"],
            "method_summary": "细节开场",
            "risk": "不扩大事实",
        }
        for i in range(1, 4)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"strategies": strategies, "recommended_index": 0}, ensure_ascii=False)}}]})

    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://api.deepseek.com", ai_api_key="secret", ai_model="deepseek-flash")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=httpx.MockTransport(handler)))

    provider.generate_strategies([{"id":"f1"},{"id":"f2"},{"id":"f3"}], ["细节开场"], "活动")

    system_prompt = requests[0]["messages"][0]["content"]
    assert '"strategies"' in system_prompt
    assert system_prompt.count('"protagonist"') == 3
    assert '"recommended_index"' in system_prompt
