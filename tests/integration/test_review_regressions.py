from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import Draft, DraftCitation, FactCard, FactSource, Material, Project, QualityIssue, SourceChunk, Strategy
from workbench.db.projects import delete_project
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.drafts.schemas import DraftPatch
from workbench.drafts.service import save_draft
from workbench.exports.markdown import ExportBlocked, write_markdown_export
from workbench.main import create_app
from workbench.quality.scanner import scan_content
from workbench.quality.service import run_quality_check
from workbench.settings import Settings
from workbench.strategies.service import generate_strategies


def seed(tmp_path: Path):
    engine = create_sqlite_engine(tmp_path / "review.db")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    project = Project(name="同名项目")
    session.add(project); session.flush()
    material = Material(project_id=project.id, file_name="source.txt", mime_type="text/plain", path="")
    session.add(material); session.flush()
    chunk = SourceChunk(material_id=material.id, content="来源")
    session.add(chunk); session.flush()
    facts = []
    for index in range(3):
        fact = FactCard(project_id=project.id, type="EVENT", content=f"已确认事实 {index}", status="CONFIRMED")
        session.add(fact); session.flush(); session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id)); facts.append(fact)
    strategy = Strategy(project_id=project.id, name="现场纪实型", angle="现场", opening="声音", structure="时间线", fact_ids=[f.id for f in facts], method_summary="细节", risk="克制", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, title="稿件", outline=[], content="<!-- block:block-1 -->\n已确认事实 0", status="CHECKED", version=1)
    session.add(draft); session.flush(); session.add(DraftCitation(draft_id=draft.id, fact_id=facts[0].id, block_id="block-1")); session.commit()
    return session, project, material, facts, strategy, draft


def test_prefix_is_scanned_and_edit_invalidates_quality(tmp_path: Path) -> None:
    issues = scan_content("联系电话 13812345678\n<!-- block:b1 -->\n正文", set(), set(), set(), [])
    assert any(issue.type == "PRIVACY_RISK" and issue.block_id == "document" for issue in issues)
    session, _, _, _, _, draft = seed(tmp_path)
    session.add(QualityIssue(draft_id=draft.id, type="PRIVACY_RISK", severity="HIGH", block_id="b", message="x")); session.commit()
    saved = save_draft(session, draft.id, DraftPatch(content=draft.content + "\n修改"))
    assert saved.status == "DRAFT"
    assert session.scalar(select(QualityIssue).where(QualityIssue.draft_id == draft.id)) is None


def test_strategy_regeneration_and_populated_project_deletion_are_fk_safe(tmp_path: Path) -> None:
    session, project, _, _, strategy, _ = seed(tmp_path)
    generated = generate_strategies(session, MockAIProvider(delay_ms=0), project.id)
    assert len(generated) == 3
    assert session.get(Strategy, strategy.id) is not None
    delete_project(session, project.id, tmp_path / "storage" / "projects")
    assert session.get(Project, project.id) is None


def test_quality_rejects_citation_without_live_source_and_exports_do_not_collide(tmp_path: Path) -> None:
    session, project, material, facts, _, draft = seed(tmp_path)
    session.delete(material); session.flush(); facts[0].status = "PENDING"; session.commit()
    issues = run_quality_check(session, MockAIProvider(delay_ms=0), draft.id)
    assert any(issue.type == "MISSING_SOURCE" for issue in issues)
    with pytest.raises(ExportBlocked, match="事实"):
        write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True)

    for issue in issues:
        issue.status = "RESOLVED"
    draft.quality_status = "PASSED"
    session.commit()

    project2 = Project(name=project.name); session.add(project2); session.flush()
    strategy2 = Strategy(project_id=project2.id, name="现场", angle="现场", opening="声音", structure="线", fact_ids=[], method_summary="", risk="", selected=True)
    session.add(strategy2); session.flush()
    draft2 = Draft(project_id=project2.id, strategy_id=strategy2.id, title="二", outline=[], content="<!-- block:x -->\n公开正文", status="CHECKED", version=1)
    session.add(draft2); session.commit()
    first = write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True)
    second = write_markdown_export(session, draft2.id, tmp_path / "exports", confirm_high=True)
    assert first != second
    assert "<!-- block:" not in second.read_text(encoding="utf-8")


def test_upload_batch_continues_after_invalid_file(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path, mock_ai_delay_ms=0)); Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "批量"}).json()["data"]
        response = client.post(f"/api/projects/{project['id']}/materials", files=[
            ("files", ("one.txt", b"one", "text/plain")),
            ("files", ("bad.exe", b"bad", "application/octet-stream")),
            ("files", ("three.txt", b"three", "text/plain")),
        ])
    data = response.json()["data"]
    assert response.status_code == 201
    assert [item.get("material", {}).get("file_name") for item in data if item.get("material")] == ["one.txt", "three.txt"]
    assert any(item.get("error") for item in data)


def test_reference_and_material_mutations_invalidate_downstream_results(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        project = Project(name="上游失效")
        session.add(project); session.flush()
        strategy = Strategy(project_id=project.id, name="现场", angle="现场", opening="声音", structure="线", fact_ids=[], method_summary="", risk="", selected=True)
        session.add(strategy); session.flush()
        draft = Draft(project_id=project.id, strategy_id=strategy.id, title="稿件", outline=[], content="正文", status="CHECKED", quality_status="PASSED", version=1, is_current=True)
        session.add(draft); session.flush()
        session.add(QualityIssue(draft_id=draft.id, type="PRIVACY_RISK", severity="HIGH", block_id="document", message="旧检查"))
        session.commit()
        project_id, draft_id = project.id, draft.id

    with TestClient(app) as client:
        reference = client.post(
            f"/api/projects/{project_id}/references",
            json={"input_type": "TEXT", "raw_text": "案例文本", "source_label": "案例"},
        ).json()["data"]
        assert client.get(f"/api/projects/{project_id}").json()["data"]["revision"] == 1
        client.patch(f"/api/references/{reference['id']}", json={"source_label": "更新案例"})
        assert client.get(f"/api/projects/{project_id}").json()["data"]["revision"] == 2
        deleted_reference = client.delete(f"/api/references/{reference['id']}")
        assert deleted_reference.status_code == 200
        assert client.get(f"/api/projects/{project_id}").json()["data"]["revision"] == 3

        uploaded = client.post(
            f"/api/projects/{project_id}/materials",
            files=[("files", ("note.txt", b"event notes", "text/plain"))],
        ).json()["data"][0]["material"]
        assert client.get(f"/api/projects/{project_id}").json()["data"]["revision"] == 4
        client.patch(f"/api/materials/{uploaded['id']}", json={"category": "NOTE"})
        assert client.get(f"/api/projects/{project_id}").json()["data"]["revision"] == 5
        client.delete(f"/api/materials/{uploaded['id']}")
        assert client.get(f"/api/projects/{project_id}").json()["data"]["revision"] == 6

    with app.state.session_factory() as session:
        draft = session.get(Draft, draft_id)
        issue = session.scalar(select(QualityIssue).where(QualityIssue.draft_id == draft_id))
    assert draft.quality_status == "STALE"
    assert issue is None
