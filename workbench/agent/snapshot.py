from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, FactCard, Material, QualityIssue, ReferenceCase, SourceChunk, Strategy


class FactEvidence(BaseModel):
    id: str
    type: str
    confidence: float
    source_count: int
    source_categories: list[str] = Field(default_factory=list)
    conflict_group: Optional[str] = None
    identity_inferred: bool = False


class ProjectSnapshot(BaseModel):
    project_id: str
    project_revision: int = 0
    goal: str = ""
    pending_material_ids: list[str] = Field(default_factory=list)
    source_chunk_count: int = 0
    fact_count: int = 0
    eligible_fact_ids: list[str] = Field(default_factory=list)
    eligible_fact_types: list[str] = Field(default_factory=list)
    conflict_groups: list[str] = Field(default_factory=list)
    pending_fact_count: int = 0
    selected_reference_count: int = 0
    unanalyzed_reference_ids: list[str] = Field(default_factory=list)
    usable_reference_count: int = 0
    allow_without_references: bool = False
    strategy_count: int = 0
    selected_strategy_id: Optional[str] = None
    draft_id: Optional[str] = None
    draft_revision: int = 0
    draft_is_stale: bool = False
    quality_status: str = "NOT_CHECKED"
    blocking_issue_count: int = 0
    auto_fixable_issue_count: int = 0


def build_project_snapshot(session: Session, project_id: str) -> ProjectSnapshot:
    from workbench.db.models import Project

    project = session.get(Project, project_id)
    if project is None:
        raise LookupError(project_id)

    materials = list(session.scalars(select(Material).where(Material.project_id == project_id)).all())
    facts = list(session.scalars(select(FactCard).where(FactCard.project_id == project_id)).all())
    eligible = [fact for fact in facts if fact.status == "CONFIRMED" and fact.conflict_group is None]
    references = list(session.scalars(select(ReferenceCase).where(ReferenceCase.project_id == project_id, ReferenceCase.selected.is_(True))).all())
    strategies = list(session.scalars(select(Strategy).where(Strategy.project_id == project_id)).all())
    draft = session.scalar(
        select(Draft).where(Draft.project_id == project_id, Draft.is_current.is_(True)).order_by(Draft.version.desc())
    )
    open_issues = []
    if draft is not None:
        open_issues = list(
            session.scalars(select(QualityIssue).where(QualityIssue.draft_id == draft.id, QualityIssue.status == "OPEN")).all()
        )

    decisions = project.decisions or {}
    return ProjectSnapshot(
        project_id=project.id,
        project_revision=project.revision,
        goal=project.goal,
        pending_material_ids=[material.id for material in materials if material.parse_status == "QUEUED"],
        source_chunk_count=session.scalar(
            select(func.count()).select_from(SourceChunk).join(Material).where(Material.project_id == project_id)
        )
        or 0,
        fact_count=len(facts),
        eligible_fact_ids=[fact.id for fact in eligible],
        eligible_fact_types=[fact.type for fact in eligible],
        conflict_groups=sorted({fact.conflict_group for fact in facts if fact.conflict_group}),
        pending_fact_count=sum(fact.status == "PENDING" for fact in facts),
        selected_reference_count=len(references),
        unanalyzed_reference_ids=[reference.id for reference in references if reference.analysis is None and reference.status == "PENDING"],
        usable_reference_count=sum(reference.analysis is not None for reference in references),
        allow_without_references=bool(decisions.get("allow_without_references")),
        strategy_count=len(strategies),
        selected_strategy_id=next((strategy.id for strategy in strategies if strategy.selected), None),
        draft_id=draft.id if draft else None,
        draft_revision=draft.revision if draft else 0,
        draft_is_stale=bool(draft and draft.status == "STALE"),
        quality_status=draft.quality_status if draft else "NOT_CHECKED",
        blocking_issue_count=sum(issue.type in {"MISSING_SOURCE", "FACT_CONFLICT"} for issue in open_issues),
        auto_fixable_issue_count=sum(issue.type == "SIMILAR_EXPRESSION" for issue in open_issues),
    )
