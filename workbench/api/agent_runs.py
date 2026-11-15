from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.recovery import retry_run
from workbench.agent.repository import ActiveRunExistsError, append_message, create_run, get_active_run, list_steps
from workbench.agent.runner import AgentRunNotFoundError, InvalidAgentRunTransition
from workbench.agent.schemas import AgentAnswer, AgentMessageCreate, AgentRunRead, AgentStepRead
from workbench.api.responses import api_error, api_response
from workbench.db.models import AgentRun, Project
from workbench.web.dependencies import get_session


router = APIRouter(prefix="/api", tags=["agent-runs"])


class StartRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


def _run_payload(run: AgentRun) -> dict:
    return AgentRunRead.model_validate(run).model_dump(mode="json")


def _get_run(session: Session, run_id: str) -> AgentRun:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise AgentRunNotFoundError(run_id)
    return run


def _schedule(background_tasks: BackgroundTasks, request: Request, run_id: str) -> None:
    background_tasks.add_task(request.app.state.agent_runner.run, run_id)


@router.post("/projects/{project_id}/agent-runs")
def start_run(
    project_id: str,
    data: StartRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    project = session.get(Project, project_id)
    if project is None:
        return api_error("PROJECT_NOT_FOUND", "没有找到这个项目", 404)
    existing = get_active_run(session, project_id)
    if existing is not None:
        return api_response(_run_payload(existing))
    project.goal = data.goal.strip()
    project.revision += 1
    session.commit()
    try:
        run = create_run(session, project_id, project.goal)
    except ActiveRunExistsError:
        return api_response(_run_payload(get_active_run(session, project_id)))
    _schedule(background_tasks, request, run.id)
    return api_response(_run_payload(run), status_code=201)


@router.get("/agent-runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)):
    try:
        return api_response(_run_payload(_get_run(session, run_id)))
    except AgentRunNotFoundError:
        return api_error("AGENT_RUN_NOT_FOUND", "没有找到这次 Agent 运行", 404)


@router.get("/agent-runs/{run_id}/steps")
def get_steps(run_id: str, session: Session = Depends(get_session)):
    try:
        _get_run(session, run_id)
    except AgentRunNotFoundError:
        return api_error("AGENT_RUN_NOT_FOUND", "没有找到这次 Agent 运行", 404)
    return api_response([AgentStepRead.model_validate(step).model_dump(mode="json") for step in list_steps(session, run_id)])


@router.post("/agent-runs/{run_id}/answers")
def answer_run(
    run_id: str,
    data: AgentAnswer,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    try:
        run = _get_run(session, run_id)
    except AgentRunNotFoundError:
        return api_error("AGENT_RUN_NOT_FOUND", "没有找到这次 Agent 运行", 404)
    if run.status != "WAITING_USER" or data.question_code != run.waiting_reason:
        return api_error("INVALID_AGENT_STATE", "当前运行不在等待这个问题的回答", 409)
    if data.question_code == "MISSING_REFERENCE" and data.selected_option_id == "continue":
        decisions = dict(run.project.decisions or {})
        decisions["allow_without_references"] = True
        run.project.decisions = decisions
        run.project.revision += 1
    append_message(
        session,
        run.id,
        AgentMessageCreate(type="USER_ANSWER", content=data.free_text or data.selected_option_id or "用户已确认", payload=data.model_dump(mode="json")),
    )
    run.status = "QUEUED"
    run.waiting_reason = None
    run.waiting_payload = None
    session.commit()
    session.refresh(run)
    _schedule(background_tasks, request, run.id)
    return api_response(_run_payload(run))


@router.post("/agent-runs/{run_id}/pause")
def pause_run(run_id: str, request: Request):
    try:
        return api_response(_run_payload(request.app.state.agent_runner.request_pause(run_id)))
    except AgentRunNotFoundError:
        return api_error("AGENT_RUN_NOT_FOUND", "没有找到这次 Agent 运行", 404)
    except InvalidAgentRunTransition:
        return api_error("INVALID_AGENT_STATE", "当前运行不能暂停", 409)


@router.post("/agent-runs/{run_id}/resume")
def resume_run(run_id: str, request: Request, background_tasks: BackgroundTasks):
    try:
        run = request.app.state.agent_runner.resume(run_id)
    except AgentRunNotFoundError:
        return api_error("AGENT_RUN_NOT_FOUND", "没有找到这次 Agent 运行", 404)
    except InvalidAgentRunTransition:
        return api_error("INVALID_AGENT_STATE", "当前运行不能恢复", 409)
    _schedule(background_tasks, request, run.id)
    return api_response(_run_payload(run))


@router.post("/agent-runs/{run_id}/cancel")
def cancel_run(run_id: str, request: Request):
    try:
        return api_response(_run_payload(request.app.state.agent_runner.request_cancel(run_id)))
    except AgentRunNotFoundError:
        return api_error("AGENT_RUN_NOT_FOUND", "没有找到这次 Agent 运行", 404)
    except InvalidAgentRunTransition:
        return api_error("INVALID_AGENT_STATE", "当前运行不能取消", 409)


@router.post("/projects/{project_id}/agent-runs/latest/retry")
def retry_latest(project_id: str, request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    latest = session.scalar(
        select(AgentRun)
        .where(AgentRun.project_id == project_id, AgentRun.status.in_({"PARTIAL", "FAILED", "CANCELLED"}))
        .order_by(AgentRun.updated_at.desc())
    )
    if latest is None:
        return api_error("NO_RETRYABLE_RUN", "没有可重试的 Agent 运行", 404)
    try:
        run = retry_run(session, latest.id)
    except (ActiveRunExistsError, ValueError):
        return api_error("INVALID_AGENT_STATE", "当前项目已有运行或不能重试", 409)
    _schedule(background_tasks, request, run.id)
    return api_response(_run_payload(run), status_code=201)
