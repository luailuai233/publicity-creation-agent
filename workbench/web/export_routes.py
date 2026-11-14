from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, QualityIssue
from workbench.db.projects import get_project
from workbench.exports.plain_text import markdown_to_plain_text
from workbench.web.dependencies import get_session


templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["export-pages"])


@router.get("/project/{project_id}/export", response_class=HTMLResponse)
def page(project_id: str, request: Request, session: Session = Depends(get_session)):
    project = get_project(session, project_id)
    draft = session.scalar(select(Draft).where(Draft.project_id == project_id, Draft.is_current.is_(True)))
    issues = [] if draft is None else list(session.scalars(select(QualityIssue).where(QualityIssue.draft_id == draft.id)).all())
    return templates.TemplateResponse(
        request=request, name="quality/page.html",
        context={"project": project, "draft": draft, "issues": issues, "plain_text": markdown_to_plain_text(draft.content) if draft else ""},
    )
