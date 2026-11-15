from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.exports.markdown import ExportBlocked, write_markdown_export
from workbench.web.dependencies import get_session


router = APIRouter(tags=["exports"])


class ExportRequest(BaseModel):
    confirm_high: bool = False


@router.post("/api/drafts/{draft_id}/export")
def export(draft_id: str, data: ExportRequest, request: Request, session: Session = Depends(get_session)):
    try:
        path = write_markdown_export(session, draft_id, request.app.state.settings.paths.exports, data.confirm_high)
        return api_response({"path": str(path), "file_name": path.name})
    except LookupError:
        return api_error("DRAFT_NOT_FOUND", "没有找到这个稿件", 404)
    except ExportBlocked as error:
        return api_error("EXPORT_BLOCKED", str(error), 409)
