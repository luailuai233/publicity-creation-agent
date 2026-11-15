from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.repository import get_active_run, list_steps
from workbench.db.models import AgentRun
from workbench.db.projects import ProjectNotFoundError, create_project, delete_project, list_projects
from workbench.domain.project_schemas import ProjectCreate
from workbench.web.dependencies import get_session


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
def agent_workspace(project_id: str, request: Request, session: Session = Depends(get_session)):
    from workbench.db.projects import get_project

    project = get_project(session, project_id)
    run = get_active_run(session, project_id) or session.scalar(
        select(AgentRun).where(AgentRun.project_id == project_id).order_by(AgentRun.updated_at.desc())
    )
    steps = list_steps(session, run.id) if run else []
    return templates.TemplateResponse(
        request=request,
        name="agent/workspace.html",
        context={"project": project, "run": run, "steps": steps},
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
