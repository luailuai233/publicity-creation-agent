from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import FactCard, FactSource, Material, SourceChunk
from workbench.facts.schemas import ConflictResolution, FactPatch
from workbench.drafts.service import invalidate_project_checks


class FactNotFoundError(LookupError):
    pass


class FactTransitionError(ValueError):
    pass


def _get_fact(session: Session, fact_id: str) -> FactCard:
    fact = session.get(FactCard, fact_id)
    if fact is None:
        raise FactNotFoundError(fact_id)
    return fact


def _validate_confirmation(session: Session, fact: FactCard, resolving_conflict: bool = False) -> None:
    if fact.status == "CONFLICT" and not resolving_conflict:
        raise FactTransitionError("请先解决冲突，再确认事实")
    source_categories = session.scalars(
        select(Material.category)
        .join(SourceChunk, SourceChunk.material_id == Material.id)
        .join(FactSource, FactSource.source_chunk_id == SourceChunk.id)
        .where(FactSource.fact_id == fact.id)
    ).all()
    if not source_categories:
        raise FactTransitionError("事实必须至少关联一个来源")
    if fact.type == "QUOTE" and not {"INTERVIEW", "SPEECH"}.intersection(source_categories):
        raise FactTransitionError("引语必须来自采访或发言稿来源")


def update_fact(session: Session, fact_id: str, patch: FactPatch) -> FactCard:
    fact = _get_fact(session, fact_id)
    if patch.content is not None:
        fact.content = patch.content.strip()
    if patch.status is not None:
        if patch.status not in {"PENDING", "CONFIRMED", "INVALID"}:
            raise FactTransitionError("不支持的事实状态")
        if patch.status == "CONFIRMED":
            _validate_confirmation(session, fact)
        fact.status = patch.status
    invalidate_project_checks(session, fact.project_id)
    session.commit()
    session.refresh(fact)
    return fact


def resolve_conflict(session: Session, group_id: str, resolution: ConflictResolution) -> FactCard:
    facts = list(session.scalars(select(FactCard).where(FactCard.conflict_group == group_id)).all())
    if not facts:
        raise FactNotFoundError(group_id)
    chosen = next((fact for fact in facts if fact.id == resolution.fact_id), None)
    if chosen is None:
        raise FactTransitionError("选择的事实不属于这个冲突组")
    _validate_confirmation(session, chosen, resolving_conflict=True)
    for fact in facts:
        fact.status = "CONFIRMED" if fact.id == chosen.id else "INVALID"
        fact.conflict_group = None
    invalidate_project_checks(session, chosen.project_id)
    session.commit()
    session.refresh(chosen)
    return chosen
