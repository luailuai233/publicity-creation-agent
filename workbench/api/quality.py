from typing import Literal
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.db.models import QualityIssue
from workbench.quality.service import QualityCheckIncomplete, run_quality_check
from workbench.web.dependencies import get_session


router = APIRouter(tags=["quality"])


class IssuePatch(BaseModel):
    status: Literal["OPEN", "RESOLVED", "ACCEPTED"]


def serialize(issue: QualityIssue) -> dict:
    return {"id": issue.id, "type": issue.type, "severity": issue.severity, "block_id": issue.block_id, "message": issue.message, "status": issue.status}


@router.post("/api/drafts/{draft_id}/check")
def check(draft_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        return api_response([serialize(issue) for issue in run_quality_check(session, request.app.state.ai_provider, draft_id)])
    except LookupError:
        return api_error("DRAFT_NOT_FOUND", "没有找到这个稿件", 404)
    except QualityCheckIncomplete as error:
        return api_error("CHECK_INCOMPLETE", str(error), 503)


@router.patch("/api/quality-issues/{issue_id}")
def update(issue_id: str, patch: IssuePatch, session: Session = Depends(get_session)):
    issue = session.get(QualityIssue, issue_id)
    if issue is None:
        return api_error("ISSUE_NOT_FOUND", "没有找到这个检查问题", 404)
    issue.status = patch.status
    session.commit(); session.refresh(issue)
    return api_response(serialize(issue))
