from pathlib import Path

from fastapi import BackgroundTasks

from workbench.agent.schemas import AgentAnswer, AgentAnswerItem
from workbench.api.agent_runs import answer_run
from workbench.db.base import Base
from workbench.db.models import AgentRun, FactCard, FactSource, Material, Project, SourceChunk
from workbench.db.session import create_session_factory, create_sqlite_engine


def test_answer_batch_rolls_back_an_earlier_conflict_when_a_later_answer_fails(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "atomic-answers.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = Project(name="原子回答")
        session.add(project)
        session.flush()
        material = Material(project_id=project.id, file_name="流程.txt", mime_type="text/plain", category="FLOW")
        session.add(material)
        session.flush()
        chunk = SourceChunk(material_id=material.id, content="人数存在冲突")
        session.add(chunk)
        session.flush()
        first = FactCard(project_id=project.id, type="NUMBER", content="36 人", status="CONFLICT", conflict_group="number-1")
        second = FactCard(project_id=project.id, type="NUMBER", content="12 人", status="CONFLICT", conflict_group="number-1")
        session.add_all([first, second])
        session.flush()
        session.add_all(
            [
                FactSource(fact_id=first.id, source_chunk_id=chunk.id),
                FactSource(fact_id=second.id, source_chunk_id=chunk.id),
            ]
        )
        run = AgentRun(
            project_id=project.id,
            goal="确认事实",
            status="WAITING_USER",
            waiting_reason="FACT_CONFLICT",
            waiting_payload={
                "project_revision": project.revision,
                "questions": [
                    {"id": "fact-conflict:number-1", "code": "FACT_CONFLICT", "affected_fact_ids": [first.id, second.id]},
                    {"id": "revise-missing", "code": "REVISE_FACT", "affected_fact_ids": ["missing-fact"]},
                ],
            },
        )
        session.add(run)
        session.commit()
        run_id = run.id
        revision = project.revision
        first_id = first.id
        second_id = second.id

        response = answer_run(
            run_id,
            AgentAnswer(
                project_revision=revision,
                answers=[
                    AgentAnswerItem(question_id="fact-conflict:number-1", selected_option_id=first_id),
                    AgentAnswerItem(question_id="revise-missing", free_text="修订值"),
                ],
            ),
            request=None,
            background_tasks=BackgroundTasks(),
            session=session,
        )

        session.expire_all()
        persisted_first = session.get(FactCard, first_id)
        persisted_second = session.get(FactCard, second_id)
        persisted_run = session.get(AgentRun, run_id)

    assert response.status_code == 422
    assert persisted_first.status == "CONFLICT"
    assert persisted_second.status == "CONFLICT"
    assert persisted_first.conflict_group == "number-1"
    assert persisted_second.conflict_group == "number-1"
    assert persisted_run.status == "WAITING_USER"
