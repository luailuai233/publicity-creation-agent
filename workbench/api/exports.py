from typing import Literal
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.exports.markdown import ExportBlocked, write_markdown_export
from workbench.exports.plain_text import write_plain_text_export
from workbench.web.dependencies import get_session


router = APIRouter(tags=["exports"])


class ExportRequest(BaseModel):
    confirm_high: bool = False
    format: Literal["markdown", "plain_text"] = "markdown"
    include_notes: bool | None = None


@router.post("/api/drafts/{draft_id}/export")
def export(draft_id: str, data: ExportRequest, request: Request, session: Session = Depends(get_session)):
    try:
        include_notes = data.include_notes if data.include_notes is not None else data.format == "markdown"
        writer = write_plain_text_export if data.format == "plain_text" else write_markdown_export
        path = writer(session, draft_id, request.app.state.settings.paths.exports, data.confirm_high, include_notes)
        return api_response({"path": str(path), "file_name": path.name})
    except LookupError:
        return api_error("DRAFT_NOT_FOUND", "没有找到这个稿件", 404)
    except ExportBlocked as error:
        return api_error("EXPORT_BLOCKED", str(error), 409)
