from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.db.models import FactCard, FactSource, Material, Project, SourceChunk
from workbench.main import create_app
from workbench.settings import Settings


def build_app(tmp_path: Path):
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    return app


def seed_conflict(app):
    with app.state.session_factory() as session:
        project = Project(name="事实 API")
        session.add(project)
        session.flush()
        material = Material(project_id=project.id, file_name="flow.txt", mime_type="text/plain", category="FLOW")
        session.add(material)
        session.flush()
        chunk = SourceChunk(material_id=material.id, content="原文：活动 9:00 开始", page=1, paragraph=4)
        session.add(chunk)
        session.flush()
        first = FactCard(project_id=project.id, type="TIME", content="活动 9:00 开始", status="CONFLICT", conflict_group="start-time")
        second = FactCard(project_id=project.id, type="TIME", content="活动 9:30 开始", status="CONFLICT", conflict_group="start-time")
        session.add_all([first, second])
        session.flush()
        session.add(FactSource(fact_id=first.id, source_chunk_id=chunk.id))
        session.commit()
        return project.id, first.id, second.id


def test_fact_api_exposes_sources_and_requires_manual_conflict_resolution(tmp_path: Path) -> None:
    app = build_app(tmp_path)
    project_id, first_id, second_id = seed_conflict(app)

    with TestClient(app) as client:
        before = client.get(f"/api/projects/{project_id}/facts").json()["data"]
        resolved = client.post(
            "/api/facts/conflicts/start-time/resolve",
            json={"fact_id": first_id},
        ).json()["data"]
        after = client.get(f"/api/projects/{project_id}/facts").json()["data"]
        page = client.get(f"/project/{project_id}/materials")

    first_before = next(item for item in before if item["id"] == first_id)
    assert first_before["status"] == "CONFLICT"
    assert first_before["sources"][0] == {"file_name": "flow.txt", "page": 1, "paragraph": 4, "content": "原文：活动 9:00 开始"}
    assert resolved["status"] == "CONFIRMED"
    assert next(item for item in after if item["id"] == second_id)["status"] == "INVALID"
    assert page.status_code == 200
    assert "解决冲突" in page.text
    assert "查看来源" in page.text
