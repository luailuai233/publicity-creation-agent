from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.recovery import retry_run
from workbench.agent.repository import ActiveRunExistsError, append_message, create_run, get_active_run, list_steps
from workbench.agent.runner import AgentRunNotFoundError, InvalidAgentRunTransition
from workbench.agent.schemas import AgentAnswer, AgentAnswerItem, AgentMessageCreate, AgentRunRead, AgentStepRead
from workbench.api.responses import api_error, api_response
from workbench.db.models import AgentRun, Project
from workbench.web.dependencies import get_session
from workbench.facts.service import FactTransitionError, create_user_supplied_fact, resolve_conflict, update_fact
from workbench.facts.schemas import ConflictResolution, FactPatch
from workbench.references.service import ReferenceCreate, create_reference


router = APIRouter(prefix="/api", tags=["agent-runs"])


class StartRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


def _run_payload(run: AgentRun) -> dict:
    payload = AgentRunRead.model_validate(run).model_dump(mode="json")
    end = run.ended_at or datetime.utcnow()
    payload["elapsed_ms"] = max(0, int((end - (run.started_at or run.updated_at)).total_seconds() * 1000))
    payload["next_action"] = {
        "WAITING_USER": "请一次回答全部待确认问题",
        "FAILED": "请检查错误后重试",
        "PARTIAL": "请检查已完成结果后重试",
        "PAUSED": "可恢复运行或继续人工编辑",
        "COMPLETED": "可查看稿件并执行发布检查",
        "CANCELLED": "可重新启动创作任务",
    }.get(run.status, "Agent 正在根据项目状态继续执行")
    return payload


def _get_run(session: Session, run_id: str) -> AgentRun:
    run = session.get(AgentRun, run_id)
    if run is None:
        raise AgentRunNotFoundError(run_id)
    return run


def _schedule(background_tasks: BackgroundTasks, request: Request, run_id: str) -> None:
    background_tasks.add_task(request.app.state.agent_runner.run, run_id)


def _step_payload(step) -> dict:
    payload = AgentStepRead.model_validate(step).model_dump(mode="json")
    payload["duration_ms"] = None if step.started_at is None else max(0, int(((step.ended_at or datetime.utcnow()) - step.started_at).total_seconds() * 1000))
    return payload


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
    return api_response([_step_payload(step) for step in list_steps(session, run_id)])


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
    if run.status != "WAITING_USER":
        return api_error("INVALID_AGENT_STATE", "当前运行不在等待这个问题的回答", 409)
    payload = run.waiting_payload or {}
    questions = payload.get("questions") or [{"id": (data.question_code or run.waiting_reason), "code": run.waiting_reason, "affected_fact_ids": []}]
    expected_revision = payload.get("project_revision")
    if expected_revision is not None and (data.project_revision != expected_revision or run.project.revision != expected_revision):
        return api_error("STALE_AGENT_ANSWER", "项目内容已变化，请刷新后重新回答", 409)
    submitted = list(data.answers)
    if not submitted and data.question_code:
        if data.question_code != run.waiting_reason:
            return api_error("INVALID_AGENT_STATE", "问题 ID 与当前等待项不匹配", 409)
        submitted = [AgentAnswerItem(question_id=questions[0]["id"], selected_option_id=data.selected_option_id, free_text=data.free_text)]
    answers = {answer.question_id: answer for answer in submitted}
    expected_ids = {question["id"] for question in questions}
    if set(answers) != expected_ids or any(not (item.selected_option_id or (item.free_text and item.free_text.strip())) for item in answers.values()):
        return api_error("INCOMPLETE_AGENT_ANSWERS", "必须一次回答当前全部问题", 422)
    try:
        for question in questions:
            answer = answers[question["id"]]
            code = question["code"]
            if code == "FACT_CONFLICT":
                group_id = question["id"].split(":", 1)[-1]
                resolve_conflict(
                    session,
                    group_id,
                    ConflictResolution(fact_id=answer.selected_option_id or ""),
                    commit=False,
                )
            elif code == "REJECT_FACT":
                update_fact(session, question["affected_fact_ids"][0], FactPatch(status="INVALID"), commit=False)
            elif code == "REVISE_FACT":
                update_fact(
                    session,
                    question["affected_fact_ids"][0],
                    FactPatch(content=answer.free_text, status="CONFIRMED"),
                    commit=False,
                )
            elif code == "MISSING_REFERENCE":
                create_reference(
                    session,
                    run.project_id,
                    ReferenceCreate(input_type="TEXT", raw_text=answer.free_text or ""),
                    commit=False,
                )
            elif code == "MISSING_FACTS":
                create_user_supplied_fact(session, run.project_id, answer.free_text or "", commit=False)
            else:
                decisions = dict(run.project.decisions or {})
                decisions[f"answer:{question['id']}"] = answer.free_text or answer.selected_option_id
                run.project.decisions = decisions
    except (FactTransitionError, ValueError, LookupError) as error:
        session.rollback()
        return api_error("INVALID_AGENT_ANSWER", str(error), 422)
    append_message(
        session,
        run.id,
        AgentMessageCreate(type="USER_ANSWER", content="用户已一次提交全部确认", payload=data.model_dump(mode="json")),
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
