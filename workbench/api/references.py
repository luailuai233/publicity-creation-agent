from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.db.models import ReferenceCase
from workbench.references.service import ReferenceAnalysisUnavailable, ReferenceCreate, ReferencePatch, analyze_reference, create_reference
from workbench.web.dependencies import get_session


router = APIRouter(tags=["references"])


def serialize(reference: ReferenceCase) -> dict:
    analysis = reference.analysis
    return {
        "id": reference.id,
        "project_id": reference.project_id,
        "input_type": reference.input_type,
        "raw_text": reference.raw_text,
        "source_label": reference.source_label,
        "status": reference.status,
        "selected": reference.selected,
        "analysis": None if analysis is None else {
            "hook": analysis.hook,
            "emotion": analysis.emotion,
            "structure": analysis.structure,
            "image_role": analysis.image_role,
            "transferable": analysis.transferable,
            "avoid": analysis.avoid,
            "is_demo": analysis.is_demo,
        },
    }


@router.get("/api/projects/{project_id}/references")
def index(project_id: str, session: Session = Depends(get_session)):
    items = session.scalars(select(ReferenceCase).where(ReferenceCase.project_id == project_id).order_by(ReferenceCase.created_at)).all()
    return api_response([serialize(item) for item in items])


@router.post("/api/projects/{project_id}/references", status_code=201)
def create(project_id: str, data: ReferenceCreate, session: Session = Depends(get_session)):
    return api_response(serialize(create_reference(session, project_id, data)), status_code=201)


@router.patch("/api/references/{reference_id}")
def update(reference_id: str, patch: ReferencePatch, session: Session = Depends(get_session)):
    reference = session.get(ReferenceCase, reference_id)
    if reference is None:
        return api_error("REFERENCE_NOT_FOUND", "没有找到这个参考案例", 404)
    for key, value in patch.model_dump(exclude_none=True).items():
        setattr(reference, key, value)
    session.commit()
    session.refresh(reference)
    return api_response(serialize(reference))


@router.post("/api/references/{reference_id}/analyze")
def analyze(reference_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        analyze_reference(session, request.app.state.ai_provider, reference_id)
    except LookupError:
        return api_error("REFERENCE_NOT_FOUND", "没有找到这个参考案例", 404)
    except ReferenceAnalysisUnavailable as error:
        return api_error("REFERENCE_NEEDS_REVIEW", str(error), 409)
    return api_response(serialize(session.get(ReferenceCase, reference_id)))
