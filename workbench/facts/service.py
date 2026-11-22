import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import FactCard, FactSource, Material, Project, SourceChunk
from workbench.facts.schemas import (
    ConflictFactOption,
    ConflictGroupDetail,
    ConflictResolution,
    ConflictSourceEvidence,
    FactPatch,
)
from workbench.drafts.service import invalidate_project_checks
from workbench.materials.categories import infer_material_category


class FactNotFoundError(LookupError):
    pass


class FactTransitionError(ValueError):
    pass


def _source_label(file_name: str, page: int | None, paragraph: int | None) -> str:
    location = []
    if page is not None:
        location.append(f"第 {page} 页")
    if paragraph is not None:
        location.append(f"第 {paragraph} 段")
    return " · ".join([file_name, *location])


def load_conflict_details(session: Session, project_id: str) -> list[ConflictGroupDetail]:
    facts = list(
        session.scalars(
            select(FactCard)
            .where(FactCard.project_id == project_id, FactCard.conflict_group.is_not(None))
            .order_by(FactCard.created_at, FactCard.id)
        ).all()
    )
    groups: dict[str, ConflictGroupDetail] = {}
    for fact in facts:
        if not fact.conflict_group:
            continue
        group = groups.setdefault(
            fact.conflict_group,
            ConflictGroupDetail(id=fact.conflict_group, fact_type=fact.type),
        )
        rows = session.execute(
            select(Material.file_name, SourceChunk.page, SourceChunk.paragraph, SourceChunk.content)
            .join(SourceChunk, SourceChunk.material_id == Material.id)
            .join(FactSource, FactSource.source_chunk_id == SourceChunk.id)
            .where(FactSource.fact_id == fact.id)
            .order_by(Material.file_name, SourceChunk.page, SourceChunk.paragraph)
        ).all()
        sources = [
            ConflictSourceEvidence(
                label=_source_label(row.file_name, row.page, row.paragraph),
                excerpt=(row.content.strip()[:220] + ("…" if len(row.content.strip()) > 220 else "")),
            )
            for row in rows
        ]
        group.options.append(ConflictFactOption(id=fact.id, content=fact.content, sources=sources))
    return list(groups.values())


def _get_fact(session: Session, fact_id: str) -> FactCard:
    fact = session.get(FactCard, fact_id)
    if fact is None:
        raise FactNotFoundError(fact_id)
    return fact


def _validate_confirmation(session: Session, fact: FactCard, resolving_conflict: bool = False) -> None:
    if fact.status == "CONFLICT" and not resolving_conflict:
        raise FactTransitionError("请先解决冲突，再确认事实")
    source_rows = session.execute(
        select(Material.category, Material.file_name)
        .join(SourceChunk, SourceChunk.material_id == Material.id)
        .join(FactSource, FactSource.source_chunk_id == SourceChunk.id)
        .where(FactSource.fact_id == fact.id)
    ).all()
    if not source_rows:
        raise FactTransitionError("事实必须至少关联一个来源")
    source_categories = {infer_material_category(row.file_name, row.category) for row in source_rows}
    if fact.type == "QUOTE" and not {"INTERVIEW", "SPEECH"}.intersection(source_categories):
        raise FactTransitionError("引语必须来自采访或发言稿来源")


def create_user_supplied_fact(session: Session, project_id: str, content: str, *, commit: bool = True) -> FactCard:
    value = content.strip()
    if not value:
        raise FactTransitionError("补充事实不能为空")
    material = Material(
        project_id=project_id,
        file_name="用户补充事实.txt",
        mime_type="text/plain",
        category="NOTE",
        parse_status="DONE",
        summary=value[:180],
        parsed_text=value,
        size_bytes=len(value.encode("utf-8")),
    )
    session.add(material)
    session.flush()
    chunk = SourceChunk(material_id=material.id, content=value, paragraph=1)
    session.add(chunk)
    session.flush()
    fingerprint = hashlib.sha256(f"{project_id}:EVENT:{value}".encode("utf-8")).hexdigest()
    fact = FactCard(
        project_id=project_id,
        type="EVENT",
        content=value,
        normalized_value=value,
        fingerprint=fingerprint,
        status="CONFIRMED",
        confidence=1.0,
    )
    session.add(fact)
    session.flush()
    session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
    invalidate_project_checks(session, project_id)
    session.get(Project, project_id).revision += 1
    if commit:
        session.commit()
    else:
        session.flush()
    session.refresh(fact)
    return fact


def update_fact(session: Session, fact_id: str, patch: FactPatch, *, commit: bool = True) -> FactCard:
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
    session.get(Project, fact.project_id).revision += 1
    if commit:
        session.commit()
    else:
        session.flush()
    session.refresh(fact)
    return fact


def resolve_conflict(session: Session, group_id: str, resolution: ConflictResolution, *, commit: bool = True) -> FactCard:
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
    session.get(Project, chosen.project_id).revision += 1
    if commit:
        session.commit()
    else:
        session.flush()
    session.refresh(chosen)
    return chosen


def auto_confirm_safe_facts(session: Session, project_id: str) -> list[FactCard]:
    facts = list(session.scalars(select(FactCard).where(FactCard.project_id == project_id, FactCard.status == "PENDING")).all())
    confirmed = []
    for fact in facts:
        source_categories = session.scalars(
            select(Material.category)
            .join(SourceChunk, SourceChunk.material_id == Material.id)
            .join(FactSource, FactSource.source_chunk_id == SourceChunk.id)
            .where(FactSource.fact_id == fact.id)
        ).all()
        if fact.conflict_group or fact.confidence < 0.7 or fact.type in {"PERSON", "ROLE"} or "PHOTO" in source_categories:
            continue
        try:
            _validate_confirmation(session, fact)
        except FactTransitionError:
            continue
        fact.status = "CONFIRMED"
        confirmed.append(fact)
    session.commit()
    return confirmed
