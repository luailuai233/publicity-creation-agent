from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from workbench.agent.schemas import AgentMessageCreate
from workbench.db.models import AgentMessage, AgentRun, AgentStep
from workbench.domain.enums import AgentRunStatus


ACTIVE_RUN_STATUSES = {
    AgentRunStatus.QUEUED.value,
    AgentRunStatus.RUNNING.value,
    AgentRunStatus.PAUSED.value,
    AgentRunStatus.WAITING_USER.value,
}


class ActiveRunExistsError(RuntimeError):
    pass


def get_active_run(session: Session, project_id: str) -> AgentRun | None:
    statement = (
        select(AgentRun)
        .where(AgentRun.project_id == project_id, AgentRun.status.in_(ACTIVE_RUN_STATUSES))
        .order_by(AgentRun.updated_at.desc())
    )
    return session.scalars(statement).first()


def create_run(session: Session, project_id: str, goal: str) -> AgentRun:
    active = get_active_run(session, project_id)
    if active is not None:
        raise ActiveRunExistsError(active.id)
    run = AgentRun(project_id=project_id, goal=goal, active_key=project_id)
    session.add(run)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ActiveRunExistsError(project_id) from exc
    session.refresh(run)
    return run


def append_message(session: Session, run_id: str, data: AgentMessageCreate) -> AgentMessage:
    message = AgentMessage(run_id=run_id, **data.model_dump(mode="json"))
    session.add(message)
    session.flush()
    return message


def list_steps(session: Session, run_id: str) -> list[AgentStep]:
    statement = select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.sequence)
    return list(session.scalars(statement).all())
