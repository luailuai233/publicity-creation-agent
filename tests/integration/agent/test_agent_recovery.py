from pathlib import Path
from threading import Event

from fastapi.testclient import TestClient
from sqlalchemy import select

from workbench.agent.recovery import recover_agent_runs, retry_run
from workbench.agent.repository import create_run
from workbench.db.base import Base
from workbench.db.models import AgentRun
from workbench.db.projects import create_project
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.domain.project_schemas import ProjectCreate
from workbench.main import create_app
from workbench.settings import Settings


def test_recovery_requeues_only_running_runs(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "recovery.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project_ids = []
        run_ids = []
        for index, status in enumerate(("RUNNING", "PAUSED", "WAITING_USER"), start=1):
            project = create_project(session, ProjectCreate(name=f"项目 {index}"))
            run = create_run(session, project.id, "完成报道")
            run.status = status
            project_ids.append(project.id)
            run_ids.append(run.id)
        session.commit()

        recovered = recover_agent_runs(session)

        states = {run.id: run.status for run in session.scalars(select(AgentRun)).all()}
    assert recovered == [run_ids[0]]
    assert states == {run_ids[0]: "QUEUED", run_ids[1]: "PAUSED", run_ids[2]: "WAITING_USER"}


def test_retry_creates_fresh_budget_and_keeps_prior_run(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "retry.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = create_project(session, ProjectCreate(name="重试项目"))
        old = create_run(session, project.id, "完成报道")
        old.status = "PARTIAL"
        old.active_key = None
        old.tool_call_count = 12
        session.commit()

        fresh = retry_run(session, old.id)

    assert fresh.id != old.id
    assert fresh.max_tool_calls == 12
    assert fresh.tool_call_count == 0
    assert fresh.goal == old.goal


def test_app_startup_schedules_recovered_running_run(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        project = create_project(session, ProjectCreate(name="重启恢复"))
        run = create_run(session, project.id, "继续完成报道")
        run.status = "RUNNING"
        session.commit()
        run_id = run.id
    scheduled = Event()
    called = []

    def record(recovered_id: str) -> None:
        called.append(recovered_id)
        scheduled.set()

    app.state.agent_runner.run = record
    with TestClient(app):
        assert scheduled.wait(2)

    assert called == [run_id]

