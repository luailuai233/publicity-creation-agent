import json
from pathlib import Path
from types import SimpleNamespace

from workbench.ai.errors import AIRequestError
from workbench.api.references import analyze
from workbench.db.base import Base
from workbench.db.models import Project
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.references.service import ReferenceCreate, create_reference


class RejectingProvider:
    def analyze_reference(self, _raw_text: str, _source_id: str):
        raise AIRequestError("AI service rejected the request with status 400")


def test_reference_analysis_returns_structured_error_when_provider_rejects_request(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "references-api.db")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    project = Project(name="模型错误处理")
    session.add(project)
    session.commit()
    reference = create_reference(session, project.id, ReferenceCreate(input_type="TEXT", raw_text="案例正文"))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ai_provider=RejectingProvider())))

    response = analyze(reference.id, request, session)

    payload = json.loads(response.body)
    assert response.status_code == 502
    assert payload["error"]["code"] == "AI_REQUEST_ERROR"
    assert payload["error"]["message"] == "模型服务拒绝了分析请求，请检查模型名称或接口兼容配置"
