from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.repository import create_run
from workbench.db.models import AgentRun


def recover_agent_runs(session: Session) -> list[str]:
    runs = list(session.scalars(select(AgentRun).where(AgentRun.status == "RUNNING").order_by(AgentRun.updated_at)).all())
    for run in runs:
        run.status = "QUEUED"
        run.error_code = "INTERRUPTED_BY_RESTART"
        run.current_stage = "服务已重启，准备从最后成功步骤恢复"
    session.commit()
    return [run.id for run in runs]


def retry_run(session: Session, run_id: str) -> AgentRun:
    old = session.get(AgentRun, run_id)
    if old is None:
        raise LookupError(run_id)
    if old.status not in {"PARTIAL", "FAILED", "CANCELLED"}:
        raise ValueError(old.status)
    return create_run(session, old.project_id, old.goal)
