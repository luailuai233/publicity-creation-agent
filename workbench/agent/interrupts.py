from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.planner import AgentAction, decide_next
from workbench.agent.snapshot import build_project_snapshot
from workbench.db.models import AgentRun, Project


def replan_waiting_run(session: Session, project_id: str) -> AgentRun | None:
    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.project_id == project_id, AgentRun.status == "WAITING_USER")
        .order_by(AgentRun.updated_at.desc())
    )
    if run is None:
        return None
    snapshot = build_project_snapshot(session, project_id)
    decision = decide_next(snapshot, run)
    if decision.action == AgentAction.ASK_USER and decision.question is not None:
        run.waiting_reason = decision.question.code
        run.waiting_payload = {
            **decision.question.model_dump(mode="json"),
            "project_revision": snapshot.project_revision,
        }
        run.current_stage = decision.reason_summary
        session.flush()
        return None
    run.status = "QUEUED"
    run.waiting_reason = None
    run.waiting_payload = None
    run.current_stage = "项目事实已更新，正在重新规划"
    session.flush()
    return run


def reconcile_resolved_conflict(session: Session, project_id: str, group_id: str) -> AgentRun | None:
    run = session.scalar(
        select(AgentRun)
        .where(AgentRun.project_id == project_id, AgentRun.status == "WAITING_USER")
        .order_by(AgentRun.updated_at.desc())
    )
    if run is None or not run.waiting_payload:
        return None
    payload = dict(run.waiting_payload)
    questions = list(payload.get("questions") or [])
    conflict_id = f"fact-conflict:{group_id}"
    remaining = [question for question in questions if question.get("id") != conflict_id]
    if len(remaining) == len(questions):
        return None

    project = session.get(Project, project_id)
    if remaining:
        run.waiting_payload = {**payload, "questions": remaining, "project_revision": project.revision}
        run.waiting_reason = remaining[0].get("code") or "USER_INPUT_REQUIRED"
        run.current_stage = f"还有 {len(remaining)} 个问题需要一次确认"
        session.flush()
        return None

    run.status = "QUEUED"
    run.waiting_reason = None
    run.waiting_payload = None
    run.current_stage = "事实冲突已处理，正在重新规划"
    session.flush()
    return run
