from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select

from workbench.agent.fingerprints import fingerprint_for
from workbench.agent.planner import AgentAction, AgentDecision
from workbench.agent.repository import create_run
from workbench.agent.runner import AgentRunner
from workbench.agent.snapshot import ProjectSnapshot
from workbench.agent.tools.base import AgentToolContext, AgentToolResult
from workbench.agent.tools.registry import ToolRegistry
from workbench.db.base import Base
from workbench.db.models import AgentRun, AgentStep, Draft, Project, Strategy
from workbench.db.projects import create_project
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.domain.project_schemas import ProjectCreate


class ProjectInput(BaseModel):
    project_id: str


class RecordingTool:
    input_model = ProjectInput

    def __init__(self, name: str, state: dict, mutate=None):
        self.name = name
        self.state = state
        self.calls = 0
        self.mutate = mutate

    def can_run(self, _snapshot) -> bool:
        return True

    def execute(self, context: AgentToolContext, data: ProjectInput) -> AgentToolResult:
        self.calls += 1
        self.state["phase"] += 1
        if self.mutate:
            self.mutate(context)
        return AgentToolResult(summary=f"{self.name} 完成", result_ref=f"{self.name}:{data.project_id}")


def build_runtime(tmp_path: Path):
    engine = create_sqlite_engine(tmp_path / "runner.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="Agent Runner"))
        project.goal = "生成活动报道"
        session.commit()
        run = create_run(session, project.id, project.goal)
    return session_factory, project.id, run.id


def simple_snapshot(project_id: str, revision: int = 0) -> ProjectSnapshot:
    return ProjectSnapshot(project_id=project_id, project_revision=revision, goal="生成活动报道")


def test_runner_rebuilds_snapshot_and_executes_multiple_selected_tools(tmp_path: Path) -> None:
    session_factory, project_id, run_id = build_runtime(tmp_path)
    state = {"phase": 0, "snapshots": 0}
    first = RecordingTool("first", state)
    second = RecordingTool("second", state)
    registry = ToolRegistry()
    registry.register(first)
    registry.register(second)

    def snapshot_builder(_session, _project_id):
        state["snapshots"] += 1
        return simple_snapshot(project_id)

    def planner(_snapshot, _run):
        if state["phase"] == 0:
            return AgentDecision(action=AgentAction.CALL_TOOL, tool_name="first", reason_summary="先执行 first")
        if state["phase"] == 1:
            return AgentDecision(action=AgentAction.CALL_TOOL, tool_name="second", reason_summary="再执行 second")
        return AgentDecision(action=AgentAction.COMPLETE, reason_summary="完成")

    AgentRunner(session_factory, registry, snapshot_builder=snapshot_builder, planner=planner).run(run_id)

    with session_factory() as session:
        run = session.get(AgentRun, run_id)
        steps = list(session.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.sequence)).all())
    assert run.status == "COMPLETED"
    assert [step.tool_name for step in steps] == ["first", "second"]
    assert all(step.status == "DONE" for step in steps)
    assert state["snapshots"] >= 3


def test_runner_stops_at_budget_and_honors_cancel_pause_boundaries(tmp_path: Path) -> None:
    session_factory, project_id, run_id = build_runtime(tmp_path)
    state = {"phase": 0}
    tool = RecordingTool("never", state)
    registry = ToolRegistry()
    registry.register(tool)
    runner = AgentRunner(
        session_factory,
        registry,
        snapshot_builder=lambda *_: simple_snapshot(project_id),
        planner=lambda *_: AgentDecision(action=AgentAction.CALL_TOOL, tool_name="never", reason_summary="继续"),
    )
    with session_factory() as session:
        run = session.get(AgentRun, run_id)
        run.tool_call_count = 12
        session.commit()

    runner.run(run_id)
    with session_factory() as session:
        capped = session.get(AgentRun, run_id)
        capped_status = capped.status
        capped.status = "QUEUED"
        capped.active_key = project_id
        capped.tool_call_count = 0
        session.commit()
    runner.request_pause(run_id)
    runner.run(run_id)
    with session_factory() as session:
        paused = session.get(AgentRun, run_id)
        paused_status = paused.status
        paused.status = "QUEUED"
        paused.pause_requested = False
        session.commit()
    runner.request_cancel(run_id)
    runner.run(run_id)

    with session_factory() as session:
        final = session.get(AgentRun, run_id)
    assert capped_status == "PARTIAL"
    assert paused_status == "PAUSED"
    assert final.status == "CANCELLED"
    assert tool.calls == 0


def test_runner_discards_result_when_user_revision_changes_during_tool(tmp_path: Path) -> None:
    session_factory, project_id, run_id = build_runtime(tmp_path)
    state = {"phase": 0}

    def user_edit(context: AgentToolContext) -> None:
        project = context.session.get(Project, context.project_id)
        project.revision += 1
        context.session.commit()

    tool = RecordingTool("slow_tool", state, mutate=user_edit)
    registry = ToolRegistry()
    registry.register(tool)
    runner = AgentRunner(
        session_factory,
        registry,
        snapshot_builder=lambda session, _: simple_snapshot(project_id, session.get(Project, project_id).revision),
        planner=lambda _snapshot, _run: (
            AgentDecision(action=AgentAction.CALL_TOOL, tool_name="slow_tool", reason_summary="执行")
            if state["phase"] == 0
            else AgentDecision(action=AgentAction.COMPLETE, reason_summary="完成")
        ),
    )

    runner.run(run_id)

    with session_factory() as session:
        step = session.scalar(select(AgentStep).where(AgentStep.run_id == run_id))
    assert step.status == "SKIPPED"
    assert step.result_ref is None
    assert "输入已被用户更新" in step.output_summary


def test_runner_removes_draft_created_from_stale_inputs(tmp_path: Path) -> None:
    session_factory, project_id, run_id = build_runtime(tmp_path)
    state = {"phase": 0}

    class DraftingTool(RecordingTool):
        def execute(self, context, data):
            self.calls += 1
            self.state["phase"] += 1
            strategy = Strategy(project_id=project_id, name="旧策略", angle="旧", opening="旧", structure="旧", fact_ids=[], method_summary="", risk="", selected=True)
            context.session.add(strategy)
            context.session.flush()
            draft = Draft(project_id=project_id, strategy_id=strategy.id, title="旧输入稿件", outline=[], content="旧内容", version=1, is_current=True)
            context.session.add(draft)
            context.session.flush()
            project = context.session.get(Project, project_id)
            project.revision += 1
            context.session.commit()
            return AgentToolResult(summary="完成", result_ref=draft.id)

    registry = ToolRegistry()
    registry.register(DraftingTool("generate_content", state))
    AgentRunner(
        session_factory,
        registry,
        snapshot_builder=lambda session, _: simple_snapshot(project_id, session.get(Project, project_id).revision),
        planner=lambda *_: AgentDecision(action=AgentAction.CALL_TOOL, tool_name="generate_content", reason_summary="生成") if state["phase"] == 0 else AgentDecision(action=AgentAction.COMPLETE, reason_summary="完成"),
    ).run(run_id)

    with session_factory() as session:
        step = session.scalar(select(AgentStep).where(AgentStep.run_id == run_id))
        draft = session.scalar(select(Draft).where(Draft.project_id == project_id, Draft.is_current.is_(True)))
    assert step.status == "SKIPPED"
    assert draft is None


def test_runner_skips_successful_step_with_same_input_fingerprint(tmp_path: Path) -> None:
    session_factory, project_id, run_id = build_runtime(tmp_path)
    state = {"phase": 0, "plans": 0}
    tool = RecordingTool("cached", state)
    registry = ToolRegistry()
    registry.register(tool)
    current_snapshot = simple_snapshot(project_id)
    fingerprint = fingerprint_for("cached", {"project_id": project_id, "snapshot": current_snapshot.model_dump(mode="json")})
    with session_factory() as session:
        session.add(
            AgentStep(
                run_id=run_id,
                sequence=1,
                tool_name="cached",
                status="DONE",
                input_fingerprint=fingerprint,
                output_summary="之前已完成",
            )
        )
        session.commit()

    def planner(_snapshot, _run):
        state["plans"] += 1
        if state["plans"] == 1:
            return AgentDecision(action=AgentAction.CALL_TOOL, tool_name="cached", reason_summary="恢复")
        return AgentDecision(action=AgentAction.COMPLETE, reason_summary="完成")

    AgentRunner(
        session_factory,
        registry,
        snapshot_builder=lambda *_: current_snapshot,
        planner=planner,
    ).run(run_id)

    assert tool.calls == 0

