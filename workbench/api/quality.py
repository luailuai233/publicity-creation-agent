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
    resolution_note: str = ""


def serialize(issue: QualityIssue) -> dict:
    return {"id": issue.id, "type": issue.type, "severity": issue.severity, "block_id": issue.block_id, "message": issue.message, "status": issue.status, "resolution_policy": issue.resolution_policy, "resolution_note": issue.resolution_note, "fragment": issue.fragment, "suggestion": issue.suggestion}


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
    if patch.status == "ACCEPTED" and issue.resolution_policy == "HARD":
        return api_error("ISSUE_NOT_ACCEPTABLE", "该问题必须修改后重新检查，不能仅确认接受", 409)
    if patch.status == "ACCEPTED" and not patch.resolution_note.strip():
        return api_error("RESOLUTION_NOTE_REQUIRED", "确认接受时需要填写说明", 422)
    issue.status = patch.status
    issue.resolution_note = patch.resolution_note.strip()
    draft = issue.draft
    open_hard = any(item.id != issue.id and item.status == "OPEN" and item.resolution_policy == "HARD" for item in draft.quality_issues)
    draft.quality_status = "BLOCKED" if (open_hard or (issue.status == "OPEN" and issue.resolution_policy == "HARD")) else "PASSED"
    session.commit(); session.refresh(issue)
    return api_response(serialize(issue))
