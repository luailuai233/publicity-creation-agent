from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

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
