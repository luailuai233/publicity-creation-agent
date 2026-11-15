from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from workbench.agent.fingerprints import fingerprint_for
from workbench.agent.planner import AgentAction, AgentDecision, decide_next
from workbench.agent.snapshot import ProjectSnapshot, build_project_snapshot
from workbench.agent.tools.base import AgentToolContext
from workbench.agent.tools.registry import ToolRegistry
from workbench.db.models import AgentRun, AgentStep, Project


ACTIVE_STATUSES = {"QUEUED", "RUNNING", "PAUSED", "WAITING_USER"}
TERMINAL_STATUSES = {"COMPLETED", "PARTIAL", "FAILED", "CANCELLED"}


class AgentRunNotFoundError(LookupError):
    pass


class InvalidAgentRunTransition(ValueError):
    pass


class AgentRunner:
    def __init__(
        self,
        session_factory: sessionmaker,
        registry: ToolRegistry,
        provider=None,
        snapshot_builder: Callable[[Session, str], ProjectSnapshot] = build_project_snapshot,
        planner: Callable[[ProjectSnapshot, AgentRun], AgentDecision] = decide_next,
    ) -> None:
        self.session_factory = session_factory
        self.registry = registry
        self.provider = provider
        self.snapshot_builder = snapshot_builder
        self.planner = planner

    def _get_run(self, session: Session, run_id: str) -> AgentRun:
        run = session.get(AgentRun, run_id)
        if run is None:
            raise AgentRunNotFoundError(run_id)
        return run

    def _finish(self, run: AgentRun, status: str, error_code: Optional[str] = None) -> None:
        run.status = status
        run.error_code = error_code
        run.active_key = None
        run.ended_at = datetime.utcnow()

    def run(self, run_id: str) -> None:
        cycles = 0
        while cycles < 64:
            cycles += 1
            with self.session_factory() as session:
                run = self._get_run(session, run_id)
                if run.status in TERMINAL_STATUSES or run.status in {"PAUSED", "WAITING_USER"}:
                    return
                if run.cancel_requested:
                    self._finish(run, "CANCELLED")
                    session.commit()
                    return
                if run.pause_requested:
                    run.status = "PAUSED"
                    run.pause_requested = False
                    session.commit()
                    return
                if run.status == "QUEUED":
                    run.status = "RUNNING"
                    run.started_at = run.started_at or datetime.utcnow()
                    session.commit()
                if run.tool_call_count >= run.max_tool_calls:
                    self._finish(run, "PARTIAL", "TOOL_CALL_LIMIT")
                    run.current_stage = f"已达到本次运行的 {run.max_tool_calls} 次工具调用上限"
                    session.commit()
                    return

                snapshot = self.snapshot_builder(session, run.project_id)
                decision = self.planner(snapshot, run)
                if decision.action == AgentAction.COMPLETE:
                    self._finish(run, "COMPLETED")
                    run.current_stage = "已完成"
                    session.commit()
                    return
                if decision.action == AgentAction.ASK_USER:
                    run.status = "WAITING_USER"
                    run.waiting_reason = decision.question.code if decision.question else "USER_INPUT_REQUIRED"
                    run.waiting_payload = decision.question.model_dump(mode="json") if decision.question else None
                    run.current_stage = decision.reason_summary
                    session.commit()
                    return
                if decision.action == AgentAction.FAIL:
                    self._finish(run, "PARTIAL", "TOOL_CALL_LIMIT" if run.tool_call_count >= run.max_tool_calls else "PLAN_FAILED")
                    run.current_stage = decision.reason_summary
                    session.commit()
                    return

                try:
                    tool = self.registry.get(decision.tool_name or "")
                    if not tool.can_run(snapshot):
                        raise InvalidAgentRunTransition(f"工具当前不可运行: {tool.name}")
                    fingerprint = fingerprint_for(
                        tool.name,
                        {"project_id": run.project_id, "snapshot": snapshot.model_dump(mode="json")},
                    )
                    completed = session.scalar(
                        select(AgentStep)
                        .join(AgentRun, AgentRun.id == AgentStep.run_id)
                        .where(
                            AgentRun.project_id == run.project_id,
                            AgentStep.tool_name == tool.name,
                            AgentStep.input_fingerprint == fingerprint,
                            AgentStep.status == "DONE",
                        )
                        .order_by(AgentStep.ended_at.desc())
                    )
                    if completed is not None:
                        continue
                    sequence = (session.scalar(select(func.max(AgentStep.sequence)).where(AgentStep.run_id == run.id)) or 0) + 1
                    step = AgentStep(
                        run_id=run.id,
                        sequence=sequence,
                        tool_name=tool.name,
                        status="PROCESSING",
                        input_fingerprint=fingerprint,
                        input_summary=decision.reason_summary,
                        started_at=datetime.utcnow(),
                    )
                    session.add(step)
                    run.current_stage = decision.reason_summary
                    session.commit()

                    data = tool.input_model.model_validate(
                        {
                            "project_id": run.project_id,
                            "run_id": run.id,
                            "mode": "revision" if snapshot.auto_fixable_issue_count and run.revision_count < run.max_revisions else "initial",
                        }
                    )
                    result = tool.execute(
                        AgentToolContext(
                            run_id=run.id,
                            project_id=run.project_id,
                            session=session,
                            provider=self.provider,
                        ),
                        data,
                    )
                    run = self._get_run(session, run_id)
                    step = session.get(AgentStep, step.id)
                    project = session.get(Project, run.project_id)
                    run.tool_call_count += 1
                    if project.revision != snapshot.project_revision:
                        step.status = "SKIPPED"
                        step.output_summary = "输入已被用户更新，丢弃旧工具结果并重新规划"
                        step.result_ref = None
                    else:
                        step.status = "DONE"
                        step.output_summary = result.summary
                        step.result_ref = result.result_ref
                    step.ended_at = datetime.utcnow()
                    session.commit()
                except Exception as exc:
                    session.rollback()
                    run = self._get_run(session, run_id)
                    processing = session.scalar(
                        select(AgentStep)
                        .where(AgentStep.run_id == run.id, AgentStep.status == "PROCESSING")
                        .order_by(AgentStep.sequence.desc())
                    )
                    if processing is not None:
                        processing.status = "FAILED"
                        processing.error_code = type(exc).__name__
                        processing.ended_at = datetime.utcnow()
                    self._finish(run, "FAILED", type(exc).__name__)
                    run.current_stage = "工具执行失败"
                    session.commit()
                    return

        with self.session_factory() as session:
            run = self._get_run(session, run_id)
            self._finish(run, "PARTIAL", "PLANNER_CYCLE_LIMIT")
            session.commit()

    def request_pause(self, run_id: str) -> AgentRun:
        with self.session_factory() as session:
            run = self._get_run(session, run_id)
            if run.status not in {"QUEUED", "RUNNING"}:
                raise InvalidAgentRunTransition(run.status)
            if run.status == "QUEUED":
                run.status = "PAUSED"
            else:
                run.pause_requested = True
            session.commit()
            session.refresh(run)
            return run

    def resume(self, run_id: str) -> AgentRun:
        with self.session_factory() as session:
            run = self._get_run(session, run_id)
            if run.status != "PAUSED":
                raise InvalidAgentRunTransition(run.status)
            run.status = "QUEUED"
            run.pause_requested = False
            session.commit()
            session.refresh(run)
            return run

    def request_cancel(self, run_id: str) -> AgentRun:
        with self.session_factory() as session:
            run = self._get_run(session, run_id)
            if run.status not in ACTIVE_STATUSES:
                raise InvalidAgentRunTransition(run.status)
            if run.status == "RUNNING":
                run.cancel_requested = True
            else:
                self._finish(run, "CANCELLED")
            session.commit()
            session.refresh(run)
            return run
