from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.planner import has_minimum_fact_set
from workbench.agent.snapshot import build_project_snapshot
from workbench.db.models import Strategy
from workbench.db.projects import get_project
from workbench.web.dependencies import get_session
from workbench.web.project_navigation import build_project_navigation


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["strategy-pages"])


@router.get("/project/{project_id}/strategy", response_class=HTMLResponse)
def page(project_id: str, request: Request, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    strategies = list(session.scalars(select(Strategy).where(Strategy.project_id == project_id)).all())
    snapshot = build_project_snapshot(session, project_id)
    can_generate_strategies = has_minimum_fact_set(snapshot.eligible_fact_types) and snapshot.usable_method_count > 0
    return templates.TemplateResponse(
        request=request,
        name="strategy/page.html",
        context={
            "project": project,
            "strategies": strategies,
            "can_generate_strategies": can_generate_strategies,
            "navigation": build_project_navigation(session, project_id, request.url.path),
        },
    )
