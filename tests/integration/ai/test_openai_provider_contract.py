import json
import httpx

from workbench.ai.http_transport import OpenAIHTTPTransport
from workbench.ai.openai_compatible_provider import OpenAICompatibleProvider
from workbench.settings import Settings


def test_real_provider_contract_uses_local_fake_transport_without_network() -> None:
    payloads = [
        {"hook":"细节开场","emotion":"克制温暖","structure":"细节到行动","image_role":"场景证据","transferable":["方法"],"avoid":["照搬"]},
        {"strategies":[
            {"name":"人物","angle":"人物行动","opening":"动作","structure":"人物线","fact_ids":["f1"],"method_summary":"细节开场","risk":"不扩大"},
            {"name":"反差","angle":"前后变化","opening":"结果","structure":"倒叙","fact_ids":["f2"],"method_summary":"细节开场","risk":"不扩大"},
            {"name":"现场","angle":"现场切面","opening":"声音","structure":"时间线","fact_ids":["f3"],"method_summary":"细节开场","risk":"不扩大"},
        ],"recommended_index":0},
        {"titles":["推荐标题"],"outline":["开头","正文"],"recommended_title_index":0},
        {"content":"正文","cited_fact_ids":["f1"]},
        {"issues":[]},
    ]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices":[{"message":{"content":json.dumps(payloads.pop(0), ensure_ascii=False)}}]})

    transport = httpx.MockTransport(handler)
    settings = Settings(ai_provider="openai_compatible", ai_base_url="https://local.test/v1", ai_api_key="secret", ai_model="model")
    provider = OpenAICompatibleProvider(settings, transport=OpenAIHTTPTransport(settings.ai_base_url, settings.ai_api_key, transport=transport))
    assert provider.analyze_reference("案例", "ref-1").status == "DONE"
    facts = [{"id":"f1"},{"id":"f2"},{"id":"f3"}]
    assert len(provider.generate_strategies(facts, ["细节开场"], "活动").result.strategies) == 3
    assert provider.generate_outline({"name":"人物"}, facts).result.titles == ["推荐标题"]
    assert provider.generate_draft("推荐标题", ["开头"], {"name":"人物"}, facts).result.cited_fact_ids == ["f1"]
    assert provider.check_quality("正文", facts, ["细节开场"]).result.issues == []
    assert payloads == []
