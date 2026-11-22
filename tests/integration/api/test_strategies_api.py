import json
from pathlib import Path
from types import SimpleNamespace

from workbench.ai.errors import AIRequestError
from workbench.api.strategies import generate
from workbench.db.base import Base
from workbench.db.models import FactCard, Project, ReferenceAnalysis, ReferenceCase
from workbench.db.session import create_session_factory, create_sqlite_engine


class RejectingStrategyProvider:
    def generate_strategies(self, _facts, _method_summaries, project_name):
        raise AIRequestError("AI service rejected the request with status 400")


def test_strategy_generation_returns_structured_error_when_provider_rejects_request(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "strategies-api.db")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    project = Project(name="策略错误处理")
    session.add(project)
    session.flush()
    session.add_all(
        [
            FactCard(project_id=project.id, type="EVENT", content="开展迎新活动", status="CONFIRMED", confidence=0.9),
            FactCard(project_id=project.id, type="NUMBER", content="36 名志愿者", status="CONFIRMED", confidence=0.9),
        ]
    )
    reference = ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="案例", selected=True, status="DONE")
    session.add(reference)
    session.flush()
    session.add(ReferenceAnalysis(reference_id=reference.id, transferable=["细节开场"], avoid=["照搬原句"]))
    session.commit()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ai_provider=RejectingStrategyProvider())))

    response = generate(project.id, request, session)

    payload = json.loads(response.body)
    assert response.status_code == 502
    assert payload["error"]["code"] == "AI_REQUEST_ERROR"
    assert payload["error"]["message"] == "模型服务拒绝了策略生成请求，请检查模型名称或接口兼容配置"
