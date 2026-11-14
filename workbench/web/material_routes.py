from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import FactCard, Material
from workbench.db.projects import get_project
from workbench.web.dependencies import get_session


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["material-pages"])


@router.get("/project/{project_id}/materials", response_class=HTMLResponse)
def page(project_id: str, request: Request, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    materials = list(session.scalars(select(Material).where(Material.project_id == project_id).order_by(Material.created_at)).all())
    facts = list(session.scalars(select(FactCard).where(FactCard.project_id == project_id).order_by(FactCard.created_at)).all())
    conflicts = {}
    for fact in facts:
        if fact.status == "CONFLICT" and fact.conflict_group:
            conflicts.setdefault(fact.conflict_group, []).append(fact)
    return templates.TemplateResponse(
        request=request,
        name="materials/page.html",
        context={
            "project": project,
            "materials": materials,
            "selected": materials[0] if materials else None,
            "facts": facts,
            "conflicts": conflicts,
        },
    )
