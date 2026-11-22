from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.db.models import Draft, Project, QualityIssue, Strategy
from workbench.main import create_app
from workbench.settings import Settings


def test_hard_issue_cannot_be_accepted_but_soft_issue_can_with_note(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path)); Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        project = Project(name="质检策略"); session.add(project); session.flush()
        strategy = Strategy(project_id=project.id, name="策略", angle="角度", opening="开头", structure="结构", fact_ids=[], method_summary="", risk="", selected=True)
        session.add(strategy); session.flush()
        draft = Draft(project_id=project.id, strategy_id=strategy.id, content="正文", status="CHECKED", quality_status="BLOCKED")
        session.add(draft); session.flush()
        hard = QualityIssue(draft_id=draft.id, type="PRIVACY_RISK", severity="HIGH", block_id="document", message="隐私", resolution_policy="HARD")
        soft = QualityIssue(draft_id=draft.id, type="SIMILAR_EXPRESSION", severity="MEDIUM", block_id="document", message="相似", resolution_policy="SOFT")
        session.add_all([hard, soft]); session.commit(); hard_id, soft_id = hard.id, soft.id
    with TestClient(app) as client:
        assert client.patch(f"/api/quality-issues/{hard_id}", json={"status": "ACCEPTED", "resolution_note": "知悉"}).status_code == 409
        response = client.patch(f"/api/quality-issues/{soft_id}", json={"status": "ACCEPTED", "resolution_note": "已人工复核"})
    assert response.status_code == 200
    assert response.json()["data"]["resolution_note"] == "已人工复核"
