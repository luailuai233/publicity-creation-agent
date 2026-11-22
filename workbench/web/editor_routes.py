from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, Strategy
from workbench.db.projects import get_project
from workbench.facts.eligibility import get_eligible_facts
from workbench.web.dependencies import get_session
from workbench.web.project_navigation import build_project_navigation


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["editor-pages"])


@router.get("/project/{project_id}/editor", response_class=HTMLResponse)
def page(project_id: str, request: Request, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    strategy = session.scalar(select(Strategy).where(Strategy.project_id == project_id, Strategy.selected.is_(True)))
    draft = session.scalar(select(Draft).where(Draft.project_id == project_id, Draft.is_current.is_(True)))
    facts = get_eligible_facts(session, project_id)
    return templates.TemplateResponse(
        request=request, name="editor/page.html",
        context={"project": project, "strategy": strategy, "draft": draft, "facts": facts, "navigation": build_project_navigation(session, project_id, request.url.path)},
    )
