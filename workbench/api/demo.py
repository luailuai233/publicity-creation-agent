from typing import Dict, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.ai.faults import FaultInjector
from workbench.ai.mock_provider import MockAIProvider
from workbench.api.responses import api_error, api_response
from workbench.db.models import Material, ReferenceCase
from workbench.demo.seed import reset_demo_project
from workbench.web.dependencies import get_session

router = APIRouter(tags=["demo"])


class FaultRequest(BaseModel):
    faults: Dict[str, List[str]] = {}


@router.post("/api/demo/reset")
def reset(request: Request, session: Session = Depends(get_session)):
    project = reset_demo_project(session, request.app.state.settings.paths.uploads)
    materials = session.scalars(select(Material).where(Material.project_id == project.id)).all()
    references = session.scalars(select(ReferenceCase).where(ReferenceCase.project_id == project.id)).all()
    return api_response({"project_id": project.id, "materials": [{"id": item.id, "file_name": item.file_name, "status": item.parse_status} for item in materials], "references": [{"id": item.id, "source_label": item.source_label} for item in references]})


@router.post("/api/demo/faults")
def faults(data: FaultRequest, request: Request):
    if request.app.state.settings.app_env == "production":
        return api_error("DEMO_ONLY", "生产环境不允许故障注入", 403)
    request.app.state.ai_provider = MockAIProvider(delay_ms=request.app.state.settings.mock_ai_delay_ms, faults=FaultInjector(data.faults))
    return api_response({"configured": sorted(data.faults)})
