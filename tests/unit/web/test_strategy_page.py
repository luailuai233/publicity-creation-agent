from pathlib import Path

from fastapi.testclient import TestClient

from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import FactCard, Project
from workbench.main import create_app
from workbench.settings import Settings
from workbench.strategies.service import generate_strategies


def test_strategy_page_renders_three_proposals_and_one_gated_cta(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        project = Project(name="策略页面")
        session.add(project)
        session.flush()
        for index in range(4):
            session.add(FactCard(project_id=project.id, type="EVENT", content=f"确认事实 {index}", status="CONFIRMED"))
        session.commit()
        project_id = project.id
        generate_strategies(session, MockAIProvider(delay_ms=0), project_id)

    with TestClient(app) as client:
        page = client.get(f"/project/{project_id}/strategy")

    assert page.status_code == 200
    assert page.text.count('class="proposal-window') == 3
    assert page.text.count('class="primary-action') == 1
    assert "生成标题与大纲" in page.text
    assert "disabled" in page.text
    for label in ("受众", "角度", "开头", "结构", "事实", "方法", "风险", "标题方向"):
        assert label in page.text
