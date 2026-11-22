from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from workbench.ai.provider import AIProvider
from workbench.ai.schemas.draft import OutlineResult
from workbench.db.models import Draft, DraftCitation, FactCard, Project, QualityIssue, Strategy
from workbench.drafts.citations import fact_has_source
from workbench.drafts.schemas import DraftPatch
from workbench.facts.eligibility import get_eligible_facts


class DraftNeedsReview(RuntimeError):
    pass


def invalidate_project_checks(session: Session, project_id: str) -> None:
    draft_ids = list(session.scalars(select(Draft.id).where(Draft.project_id == project_id)).all())
    if draft_ids:
        session.execute(delete(QualityIssue).where(QualityIssue.draft_id.in_(draft_ids)))
        session.execute(update(Draft).where(Draft.id.in_(draft_ids)).values(status="DRAFT", quality_status="STALE"))


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


def generate_draft(session: Session, provider: AIProvider, project_id: str, title: str, outline: list[str], revision: bool = False) -> Draft:
    strategy = _selected_strategy(session, project_id)
    facts = _strategy_facts(session, strategy)
    project = session.get(Project, project_id)
    envelope = provider.generate_draft(
        title,
        outline,
        {"name": strategy.name, "structure": strategy.structure, "revision": revision, "goal": project.goal, "audience": project.audience, "tone": project.tone},
        facts,
    )
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
        draft.undo_snapshot = None
        draft.status = "DRAFT"
        draft.quality_status = "STALE"
        draft.revision += 1
        session.execute(delete(QualityIssue).where(QualityIssue.draft_id == draft.id))
        project = session.get(Project, draft.project_id)
        project.revision += 1
    session.commit()
    session.refresh(draft)
    return draft


def _block_span(content: str, block_id: str) -> tuple[int, int, str]:
    import re

    marker = re.compile(rf"<!--\s*block:{re.escape(block_id)}\s*-->")
    match = marker.search(content)
    if match is None:
        raise DraftNeedsReview("没有找到要改写的段落")
    next_marker = re.search(r"<!--\s*block:[\w-]+\s*-->", content[match.end():])
    end = match.end() + next_marker.start() if next_marker else len(content)
    return match.start(), end, content[match.end():end].strip()


def _invalidate_after_rewrite(session: Session, draft: Draft) -> None:
    draft.status = "DRAFT"
    draft.quality_status = "STALE"
    draft.revision += 1
    session.execute(delete(QualityIssue).where(QualityIssue.draft_id == draft.id))
    project = session.get(Project, draft.project_id)
    project.revision += 1


def rewrite_paragraph(session: Session, provider: AIProvider, draft_id: str, block_id: str, goal: str, expected_revision: int) -> Draft:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise LookupError(draft_id)
    if draft.revision != expected_revision:
        raise DraftNeedsReview("稿件已被修改，请刷新后重试")
    if block_id in (draft.locked_block_ids or []):
        raise DraftNeedsReview("该段落已锁定")
    start, end, paragraph = _block_span(draft.content, block_id)
    strategy = session.get(Strategy, draft.strategy_id)
    facts = _strategy_facts(session, strategy)
    allowed = {fact["id"]: fact for fact in facts}
    envelope = provider.rewrite_paragraph(paragraph, goal, facts, draft.locked_fact_ids or [])
    if envelope.status != "DONE" or envelope.result is None:
        raise DraftNeedsReview("段落改写未完成，请重试")
    if any(fact_id not in allowed for fact_id in envelope.result.cited_fact_ids):
        raise DraftNeedsReview("改写引用了未允许的事实")
    for fact_id in draft.locked_fact_ids or []:
        fact = session.get(FactCard, fact_id)
        if fact and fact.content in paragraph and fact.content not in envelope.result.content:
            raise DraftNeedsReview("改写改变了已锁定事实")
    old_citations = [{"fact_id": item.fact_id, "block_id": item.block_id} for item in draft.citations]
    draft.undo_snapshot = {"content": draft.content, "citations": old_citations}
    marker = f"<!-- block:{block_id} -->\n"
    draft.content = draft.content[:start] + marker + envelope.result.content.strip() + "\n" + draft.content[end:]
    session.execute(delete(DraftCitation).where(DraftCitation.draft_id == draft.id, DraftCitation.block_id == block_id))
    for fact_id in envelope.result.cited_fact_ids:
        session.add(DraftCitation(draft_id=draft.id, fact_id=fact_id, block_id=block_id))
    _invalidate_after_rewrite(session, draft)
    session.commit()
    session.refresh(draft)
    return draft


def undo_last_rewrite(session: Session, draft_id: str) -> Draft:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise LookupError(draft_id)
    snapshot = draft.undo_snapshot
    if not snapshot:
        raise DraftNeedsReview("没有可撤销的 Agent 改写")
    draft.content = snapshot["content"]
    session.execute(delete(DraftCitation).where(DraftCitation.draft_id == draft.id))
    for item in snapshot.get("citations", []):
        session.add(DraftCitation(draft_id=draft.id, fact_id=item["fact_id"], block_id=item["block_id"]))
    draft.undo_snapshot = None
    _invalidate_after_rewrite(session, draft)
    session.commit()
    session.refresh(draft)
    return draft
