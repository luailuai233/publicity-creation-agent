from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.db.models import Project, Strategy
from workbench.main import create_app
from workbench.settings import Settings


def test_strategy_page_renders_three_proposals_and_one_gated_cta(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        project = Project(name="策略页面")
        session.add(project)
        session.flush()
        for index in range(3):
            session.add(Strategy(project_id=project.id, name=f"提案 {index + 1}", protagonist=f"主角 {index + 1}", angle="现场", opening=f"开头 {index + 1}", structure=f"结构 {index + 1}", fact_ids=[], method_summary="人物视角", risk="注意事实", selected=False))
        session.commit()
        project_id = project.id

    with TestClient(app) as client:
        page = client.get(f"/project/{project_id}/strategy")

    assert page.status_code == 200
    assert page.text.count('class="proposal-window') == 3
    assert page.text.count('class="primary-action') == 0
    assert "Agent 推荐" in page.text
    assert "生成标题与大纲" not in page.text
    for label in ("受众", "角度", "开头", "结构", "事实", "方法", "风险", "标题方向"):
        assert label in page.text
