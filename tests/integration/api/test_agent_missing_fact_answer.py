from pathlib import Path
from types import SimpleNamespace

from fastapi import BackgroundTasks
from sqlalchemy import select

from workbench.agent.schemas import AgentAnswer, AgentAnswerItem
from workbench.api.agent_runs import answer_run
from workbench.db.base import Base
from workbench.db.models import AgentRun, FactCard, FactSource, Material, Project, SourceChunk
from workbench.db.session import create_session_factory, create_sqlite_engine


def test_missing_fact_answer_creates_a_confirmed_sourced_activity_fact(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "missing-fact.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = Project(name="补充事实")
        session.add(project)
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
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(agent_runner=SimpleNamespace(run=lambda _run_id: None))))

        response = answer_run(
            run.id,
            AgentAnswer(
                project_revision=project.revision,
                answers=[AgentAnswerItem(question_id="missing-facts", free_text="本次活动是支教团迎新交流会。")],
            ),
            request=request,
            background_tasks=BackgroundTasks(),
            session=session,
        )

        fact = session.scalar(select(FactCard).where(FactCard.project_id == project.id, FactCard.type == "EVENT"))
        material = session.scalar(select(Material).where(Material.project_id == project.id, Material.file_name == "用户补充事实.txt"))
        source = session.scalar(select(FactSource).where(FactSource.fact_id == fact.id)) if fact else None
        chunk = session.get(SourceChunk, source.source_chunk_id) if source else None
        session.refresh(run)

    assert response.status_code == 200
    assert fact is not None and fact.status == "CONFIRMED"
    assert fact.content == "本次活动是支教团迎新交流会。"
    assert material is not None and material.category == "NOTE"
    assert chunk is not None and chunk.content == fact.content
    assert run.status == "QUEUED"
