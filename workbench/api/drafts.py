from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.drafts.schemas import DraftPatch
from workbench.drafts.service import DraftNeedsReview, create_outline, generate_draft, save_draft
from workbench.web.dependencies import get_session


router = APIRouter(tags=["drafts"])


class DraftGenerateRequest(BaseModel):
    title: str
    outline: list[str]


def serialize(draft) -> dict:
    return {
        "id": draft.id, "project_id": draft.project_id, "strategy_id": draft.strategy_id,
        "title": draft.title, "outline": draft.outline, "content": draft.content,
        "version": draft.version, "status": draft.status, "is_current": draft.is_current,
        "updated_at": draft.updated_at.strftime("%H:%M:%S"),
        "word_count": len("".join(draft.content.split())),
        "citation_count": len(draft.citations),
    }


@router.post("/api/projects/{project_id}/drafts/outline")
def outline(project_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        result = create_outline(session, request.app.state.ai_provider, project_id)
        return api_response(result.model_dump())
    except DraftNeedsReview as error:
        return api_error("DRAFT_NEEDS_REVIEW", str(error), 409)


@router.post("/api/projects/{project_id}/drafts/generate")
def generate(project_id: str, data: DraftGenerateRequest, request: Request, session: Session = Depends(get_session)):
    try:
        return api_response(serialize(generate_draft(session, request.app.state.ai_provider, project_id, data.title, data.outline)), status_code=201)
    except DraftNeedsReview as error:
        return api_error("DRAFT_NEEDS_REVIEW", str(error), 409)


@router.patch("/api/drafts/{draft_id}")
def update(draft_id: str, patch: DraftPatch, session: Session = Depends(get_session)):
    try:
        return api_response(serialize(save_draft(session, draft_id, patch)))
    except LookupError:
        return api_error("DRAFT_NOT_FOUND", "没有找到这个稿件", 404)
