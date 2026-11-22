from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.repository import get_active_run, list_steps
from workbench.agent.interrupts import replan_waiting_run
from workbench.db.models import AgentRun
from workbench.db.projects import ProjectNotFoundError, create_project, delete_project, list_projects
from workbench.domain.project_schemas import ProjectCreate
from workbench.facts.service import load_conflict_details
from workbench.web.dependencies import get_session
from workbench.web.project_navigation import build_project_navigation


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(
        request=request,
        name="projects/index.html",
        context={"projects": list_projects(session), "product_name": "热点驱动宣传创作工作台"},
    )


@router.get("/project/{project_id}/agent", response_class=HTMLResponse)
def agent_workspace(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    from workbench.db.projects import get_project

    project = get_project(session, project_id)
    run = get_active_run(session, project_id) or session.scalar(
        select(AgentRun).where(AgentRun.project_id == project_id).order_by(AgentRun.updated_at.desc())
    )
    if run is not None and run.status == "WAITING_USER":
        resumed_run = replan_waiting_run(session, project_id)
        session.commit()
        if resumed_run is not None:
            background_tasks.add_task(request.app.state.agent_runner.run, resumed_run.id)
    steps = list_steps(session, run.id) if run else []
    conflict_details = {item.id: item for item in load_conflict_details(session, project_id)}
    agent_questions = []
    if run and run.waiting_payload:
        for stored in run.waiting_payload.get("questions", []):
            question = dict(stored)
            if question.get("code") == "FACT_CONFLICT":
                group_id = question.get("id", "").split(":", 1)[-1]
                detail = conflict_details.get(group_id)
                if detail is not None:
                    type_labels = {"NUMBER": "人数信息", "TIME": "时间信息", "LOCATION": "地点信息", "QUOTE": "引语内容"}
                    question.update(
                        {
                            "prompt": f"{type_labels.get(detail.fact_type, '事实内容')}存在冲突，请选择正确的一项",
                            "reason": "不同材料给出了不一致的信息；选择后，未选项会标记为无效。",
                            "affected_fact_ids": [option.id for option in detail.options],
                            "options": [
                                {
                                    "id": option.id,
                                    "label": option.content,
                                    "evidence": [f"{source.label}：{source.excerpt}" for source in option.sources],
                                }
                                for option in detail.options
                            ],
                        }
                    )
            agent_questions.append(question)
    return templates.TemplateResponse(
        request=request,
        name="agent/workspace.html",
        context={
            "project": project,
            "run": run,
            "steps": steps,
            "agent_questions": agent_questions,
            "navigation": build_project_navigation(session, project_id, request.url.path),
        },
    )


@router.post("/projects", response_class=HTMLResponse)
def create_from_page(request: Request, name: str = Form(...), session: Session = Depends(get_session)):
    if name.strip():
        create_project(session, ProjectCreate(name=name.strip()))
    return templates.TemplateResponse(
        request=request,
        name="projects/recent_projects.html",
        context={"projects": list_projects(session)},
    )


@router.delete("/projects/{project_id}")
def delete_from_page(project_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        delete_project(session, project_id, request.app.state.settings.paths.uploads)
    except ProjectNotFoundError:
        pass
    return Response(status_code=204)
