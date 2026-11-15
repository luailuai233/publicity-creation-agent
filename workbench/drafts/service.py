from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from workbench.ai.provider import AIProvider
from workbench.ai.schemas.draft import OutlineResult
from workbench.db.models import Draft, DraftCitation, QualityIssue, Strategy
from workbench.drafts.citations import fact_has_source
from workbench.drafts.schemas import DraftPatch
from workbench.facts.eligibility import get_eligible_facts


class DraftNeedsReview(RuntimeError):
    pass


def invalidate_project_checks(session: Session, project_id: str) -> None:
    draft_ids = list(session.scalars(select(Draft.id).where(Draft.project_id == project_id)).all())
    if draft_ids:
        session.execute(delete(QualityIssue).where(QualityIssue.draft_id.in_(draft_ids)))
        session.execute(update(Draft).where(Draft.id.in_(draft_ids)).values(status="DRAFT"))


def _selected_strategy(session: Session, project_id: str) -> Strategy:
    strategy = session.scalar(select(Strategy).where(Strategy.project_id == project_id, Strategy.selected.is_(True)))
    if strategy is None:
        raise DraftNeedsReview("请先选择一个创作策略")
    return strategy


def _strategy_facts(session: Session, strategy: Strategy) -> list[dict]:
    eligible = {fact.id: fact for fact in get_eligible_facts(session, strategy.project_id)}
    if any(fact_id not in eligible or not fact_has_source(session, fact_id) for fact_id in strategy.fact_ids):
        raise DraftNeedsReview("策略引用的事实已失效，请重新确认事实并生成策略")
    return [eligible[fact_id].model_dump() for fact_id in strategy.fact_ids]


def create_outline(session: Session, provider: AIProvider, project_id: str) -> OutlineResult:
    strategy = _selected_strategy(session, project_id)
    facts = _strategy_facts(session, strategy)
    envelope = provider.generate_outline({"name": strategy.name, "structure": strategy.structure}, facts)
    if envelope.status != "DONE" or envelope.result is None:
        raise DraftNeedsReview("标题与大纲生成未完成，请重试")
    return envelope.result


def generate_draft(session: Session, provider: AIProvider, project_id: str, title: str, outline: list[str]) -> Draft:
    strategy = _selected_strategy(session, project_id)
    facts = _strategy_facts(session, strategy)
    envelope = provider.generate_draft(title, outline, {"name": strategy.name, "structure": strategy.structure}, facts)
    if envelope.status != "DONE" or envelope.result is None:
        raise DraftNeedsReview("正文生成未完成，已保留现有稿件")
    current_version = session.scalar(select(func.coalesce(func.max(Draft.version), 0)).where(Draft.project_id == project_id))
    session.execute(update(Draft).where(Draft.project_id == project_id).values(is_current=False))
    draft = Draft(
        project_id=project_id, strategy_id=strategy.id, title=title, outline=outline,
        content=envelope.result.content, version=int(current_version) + 1, status="DRAFT", quality_status="NOT_CHECKED", is_current=True,
    )
    session.add(draft)
    session.flush()
    for index, fact_id in enumerate(envelope.result.cited_fact_ids, start=1):
        session.add(DraftCitation(draft_id=draft.id, fact_id=fact_id, block_id=f"block-{index}"))
    session.commit()
    session.refresh(draft)
    return draft


def save_draft(session: Session, draft_id: str, patch: DraftPatch) -> Draft:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise LookupError(draft_id)
    changes = patch.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(draft, key, value)
    if any(key in changes for key in ("title", "outline", "content")):
        draft.status = "DRAFT"
        draft.quality_status = "STALE"
        draft.revision += 1
        session.execute(delete(QualityIssue).where(QualityIssue.draft_id == draft.id))
    session.commit()
    session.refresh(draft)
    return draft
