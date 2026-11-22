from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.ai.provider import AIProvider
from workbench.db.models import ReferenceAnalysis, ReferenceCase
from workbench.db.projects import touch_project_inputs
from workbench.references.fetcher import ReferenceFetchError, SafeReferenceFetcher
from workbench.storage.local import LocalStorage
from workbench.materials.image_understanding import ImageUnderstandingError, understand_image


class ReferenceCreate(BaseModel):
    input_type: str
    raw_text: str = ""
    source_url: str = ""
    raw_path: str = ""
    source_label: str = ""
    selected: bool = True

    @model_validator(mode="after")
    def validate_input(self):
        if self.input_type not in {"TEXT", "LINK", "SCREENSHOT"}:
            raise ValueError("input_type must be TEXT, LINK, or SCREENSHOT")
        if self.input_type == "TEXT" and not self.raw_text.strip():
            raise ValueError("TEXT reference requires raw_text")
        if self.input_type == "LINK" and not self.source_url.strip():
            raise ValueError("LINK reference requires source_url")
        if self.input_type == "SCREENSHOT" and not self.raw_path.strip():
            raise ValueError("SCREENSHOT reference requires raw_path")
        return self


class ReferencePatch(BaseModel):
    raw_text: Optional[str] = Field(default=None, min_length=1)
    source_label: Optional[str] = None
    selected: Optional[bool] = None


class ReferenceAnalysisUnavailable(RuntimeError):
    pass


def create_reference(
    session: Session,
    project_id: str,
    data: ReferenceCreate,
    fetcher: SafeReferenceFetcher | None = None,
    provider=None,
    *,
    commit: bool = True,
) -> ReferenceCase:
    values = data.model_dump()
    status = "PENDING"
    fetch_status = "NOT_REQUIRED"
    if data.input_type == "LINK":
        try:
            values["raw_text"] = (fetcher or SafeReferenceFetcher()).fetch(data.source_url)
            fetch_status = "DONE"
        except ReferenceFetchError:
            fetch_status = "FAILED"
            status = "NEEDS_REVIEW"
    elif data.input_type == "SCREENSHOT" and not data.raw_text.strip():
        try:
            image_result = understand_image(Path(data.raw_path), provider=provider)
            values["raw_text"] = image_result.text
            status = image_result.status
        except ImageUnderstandingError:
            status = "NEEDS_REVIEW"
    reference = ReferenceCase(project_id=project_id, **values, status=status, fetch_status=fetch_status)
    session.add(reference)
    touch_project_inputs(session, project_id)
    if commit:
        session.commit()
    else:
        session.flush()
    session.refresh(reference)
    return reference


def delete_reference(session: Session, storage: LocalStorage, reference_id: str) -> None:
    reference = session.get(ReferenceCase, reference_id)
    if reference is None:
        raise LookupError(reference_id)
    project_id = reference.project_id
    if reference.raw_path:
        storage.delete_file(Path(reference.raw_path))
    session.delete(reference)
    touch_project_inputs(session, project_id)
    session.commit()


def analyze_reference(session: Session, provider: AIProvider, reference_id: str) -> ReferenceAnalysis:
    reference = session.get(ReferenceCase, reference_id)
    if reference is None:
        raise LookupError(reference_id)
    if not reference.raw_text.strip():
        reference.status = "NEEDS_REVIEW"
        session.commit()
        raise ReferenceAnalysisUnavailable("请先补充案例正文或截图说明")
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
    analysis.is_demo = envelope.is_demo
    session.add(analysis)
    reference.status = "DONE"
    session.commit()
    session.refresh(analysis)
    return analysis
