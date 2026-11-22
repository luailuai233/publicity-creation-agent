from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.planner import has_minimum_fact_set
from workbench.agent.snapshot import build_project_snapshot
from workbench.db.models import ReferenceCase
from workbench.db.projects import get_project
from workbench.web.dependencies import get_session
from workbench.web.project_navigation import build_project_navigation


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["inspiration-pages"])


@router.get("/project/{project_id}/inspiration", response_class=HTMLResponse)
def page(project_id: str, request: Request, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    references = list(session.scalars(select(ReferenceCase).where(ReferenceCase.project_id == project_id).order_by(ReferenceCase.created_at).limit(3)).all())
    active_reference = next((item for item in reversed(references) if item.analysis is not None), None)
    snapshot = build_project_snapshot(session, project_id)
    can_generate_strategies = (
        active_reference is not None
        and has_minimum_fact_set(snapshot.eligible_fact_types)
        and snapshot.usable_method_count > 0
    )
    return templates.TemplateResponse(
        request=request,
        name="inspiration/page.html",
        context={
            "project": project,
            "references": references,
            "active_analysis": None if active_reference is None else active_reference.analysis,
            "can_generate_strategies": can_generate_strategies,
            "navigation": build_project_navigation(session, project_id, request.url.path),
        },
    )
