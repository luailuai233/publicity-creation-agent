from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Strategy
from workbench.db.projects import get_project
from workbench.web.dependencies import get_session


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["strategy-pages"])


@router.get("/project/{project_id}/strategy", response_class=HTMLResponse)
def page(project_id: str, request: Request, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    strategies = list(session.scalars(select(Strategy).where(Strategy.project_id == project_id)).all())
    return templates.TemplateResponse(request=request, name="strategy/page.html", context={"project": project, "strategies": strategies})
