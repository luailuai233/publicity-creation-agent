from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.ai.provider import AIProvider
from workbench.db.models import ReferenceAnalysis, ReferenceCase


class ReferenceCreate(BaseModel):
    input_type: str
    raw_text: str = Field(min_length=1)
    source_label: str = ""
    selected: bool = True


class ReferencePatch(BaseModel):
    raw_text: Optional[str] = Field(default=None, min_length=1)
    source_label: Optional[str] = None
    selected: Optional[bool] = None


class ReferenceAnalysisUnavailable(RuntimeError):
    pass


def create_reference(session: Session, project_id: str, data: ReferenceCreate) -> ReferenceCase:
    reference = ReferenceCase(project_id=project_id, **data.model_dump(), status="PENDING")
    session.add(reference)
    session.commit()
    session.refresh(reference)
    return reference


def analyze_reference(session: Session, provider: AIProvider, reference_id: str) -> ReferenceAnalysis:
    reference = session.get(ReferenceCase, reference_id)
    if reference is None:
        raise LookupError(reference_id)
    envelope = provider.analyze_reference(reference.raw_text, reference.id)
    previous = session.scalar(select(ReferenceAnalysis).where(ReferenceAnalysis.reference_id == reference.id))
    if envelope.status != "DONE" or envelope.result is None:
        reference.status = "NEEDS_REVIEW"
        session.commit()
        if previous is not None:
            return previous
        raise ReferenceAnalysisUnavailable("模拟分析未完成，请人工编辑")
    result = envelope.result
    analysis = previous or ReferenceAnalysis(reference_id=reference.id)
    analysis.hook = result.hook
    analysis.emotion = result.emotion
    analysis.structure = result.structure
    analysis.image_role = result.image_role
    analysis.transferable = result.transferable
    analysis.avoid = result.avoid
    analysis.is_demo = True
    session.add(analysis)
    reference.status = "DONE"
    session.commit()
    session.refresh(analysis)
    return analysis
