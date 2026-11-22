from pathlib import Path
from types import SimpleNamespace

from fastapi import BackgroundTasks

from workbench.api.facts import resolve, update
from workbench.db.base import Base
from workbench.db.models import AgentRun, FactCard, FactSource, Material, Project, SourceChunk
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.facts.schemas import ConflictResolution, FactPatch


def test_standalone_conflict_resolution_removes_the_stale_agent_question(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "conflict-reconcile.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = Project(name="恢复冲突")
        session.add(project)
        session.flush()
        material = Material(project_id=project.id, file_name="流程.txt", mime_type="text/plain", category="FLOW")
        session.add(material)
        session.flush()
        chunk = SourceChunk(material_id=material.id, content="人数来源")
        session.add(chunk)
        session.flush()
        first = FactCard(project_id=project.id, type="NUMBER", content="36 人", status="CONFLICT", conflict_group="number-1")
        second = FactCard(project_id=project.id, type="NUMBER", content="12 人", status="CONFLICT", conflict_group="number-1")
        session.add_all([first, second])
        session.flush()
        session.add_all([FactSource(fact_id=first.id, source_chunk_id=chunk.id), FactSource(fact_id=second.id, source_chunk_id=chunk.id)])
        run = AgentRun(
            project_id=project.id,
            goal="继续创作",
            status="WAITING_USER",
            waiting_reason="FACT_CONFLICT",
            active_key=project.id,
            waiting_payload={
                "project_revision": project.revision,
                "questions": [
                    {"id": "fact-conflict:number-1", "code": "FACT_CONFLICT", "affected_fact_ids": [first.id, second.id]},
                    {"id": "missing-facts", "code": "MISSING_FACTS", "affected_fact_ids": []},
                ],
            },
        )
        session.add(run)
        session.commit()
        run_id = run.id

        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(agent_runner=SimpleNamespace(run=lambda _run_id: None))))
        response = resolve(
            "number-1",
            ConflictResolution(fact_id=first.id),
            request=request,
            background_tasks=BackgroundTasks(),
            session=session,
        )

        session.expire_all()
        persisted_run = session.get(AgentRun, run_id)
        persisted_project = session.get(Project, project.id)

    assert response.status_code == 200
    assert persisted_run.status == "WAITING_USER"
    assert [item["id"] for item in persisted_run.waiting_payload["questions"]] == ["missing-facts"]
    assert persisted_run.waiting_reason == "MISSING_FACTS"
    assert persisted_run.waiting_payload["project_revision"] == persisted_project.revision


def test_standalone_fact_update_refreshes_the_waiting_question_revision(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "fact-update-reconcile.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = Project(name="同步事实版本")
        session.add(project)
        session.flush()
        fact = FactCard(project_id=project.id, type="QUOTE", content="候选引语", status="PENDING")
        session.add(fact)
        session.flush()
        run = AgentRun(
            project_id=project.id,
            goal="继续创作",
            status="WAITING_USER",
            waiting_reason="MISSING_FACTS",
            active_key=project.id,
            waiting_payload={
                "project_revision": project.revision,
                "questions": [{"id": "missing-facts", "code": "MISSING_FACTS", "affected_fact_ids": []}],
            },
        )
        session.add(run)
        session.commit()
        run_id = run.id

        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(agent_runner=SimpleNamespace(run=lambda _run_id: None))))
        response = update(
            fact.id,
            FactPatch(status="INVALID"),
            request=request,
            background_tasks=BackgroundTasks(),
            session=session,
        )

        session.expire_all()
        persisted_run = session.get(AgentRun, run_id)
        persisted_project = session.get(Project, project.id)

    assert response.status_code == 200
    assert persisted_run.status == "WAITING_USER"
    assert persisted_run.waiting_payload["project_revision"] == persisted_project.revision
