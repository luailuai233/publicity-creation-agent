from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from workbench.agent.repository import ActiveRunExistsError, append_message, create_run, get_active_run, list_steps
from workbench.agent.schemas import AgentMessageCreate
from workbench.db.base import Base
from workbench.db.models import AgentMessage, AgentRun, AgentStep
from workbench.db.projects import create_project, delete_project
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.domain.project_schemas import ProjectCreate


@pytest.fixture()
def session_factory(tmp_path: Path):
    engine = create_sqlite_engine(tmp_path / "agent.db")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


def test_project_has_only_one_active_agent_run(session_factory) -> None:
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="校园开放日"))
        first = create_run(session, project.id, "生成真实温暖的活动长图文")

        with pytest.raises(ActiveRunExistsError):
            create_run(session, project.id, "再次启动")

        assert get_active_run(session, project.id).id == first.id


def test_agent_step_sequence_is_unique_within_run(session_factory) -> None:
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="志愿活动"))
        run = create_run(session, project.id, "整理活动报道")
        session.add(AgentStep(run_id=run.id, sequence=1, tool_name="parse_materials"))
        session.commit()
        session.add(AgentStep(run_id=run.id, sequence=1, tool_name="validate_facts"))

        with pytest.raises(IntegrityError):
            session.commit()


def test_repository_lists_steps_and_accepts_only_public_messages(session_factory) -> None:
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="社区市集"))
        run = create_run(session, project.id, "完成市集宣传稿")
        session.add_all(
            [
                AgentStep(run_id=run.id, sequence=2, tool_name="validate_facts"),
                AgentStep(run_id=run.id, sequence=1, tool_name="parse_materials"),
            ]
        )
        append_message(session, run.id, AgentMessageCreate(type="PLAN", content="整理事实，再生成正文"))
        session.commit()

        assert [step.sequence for step in list_steps(session, run.id)] == [1, 2]
        assert session.scalar(select(func.count()).select_from(AgentMessage)) == 1


def test_deleting_project_cascades_agent_records(session_factory, tmp_path: Path) -> None:
    uploads_root = tmp_path / "storage" / "projects"
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="待删除 Agent 项目"))
        run = create_run(session, project.id, "生成报道")
        session.add(AgentStep(run_id=run.id, sequence=1, tool_name="parse_materials"))
        append_message(session, run.id, AgentMessageCreate(type="STATUS", content="已启动"))
        session.commit()

        delete_project(session, project.id, uploads_root)

        assert session.scalar(select(func.count()).select_from(AgentRun)) == 0
        assert session.scalar(select(func.count()).select_from(AgentStep)) == 0
        assert session.scalar(select(func.count()).select_from(AgentMessage)) == 0
