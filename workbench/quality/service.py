from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from workbench.ai.provider import AIProvider
from workbench.db.models import Draft, DraftCitation, FactCard, FactSource, QualityIssue, ReferenceCase, Strategy
from workbench.facts.eligibility import get_eligible_facts
from workbench.quality.scanner import scan_content


class QualityCheckIncomplete(RuntimeError):
    pass


def run_quality_check(session: Session, provider: AIProvider, draft_id: str) -> list[QualityIssue]:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise LookupError(draft_id)
    sourced_terms = set(
        session.scalars(
            select(FactCard.content)
            .join(DraftCitation, DraftCitation.fact_id == FactCard.id)
            .join(FactSource, FactSource.fact_id == FactCard.id)
            .where(DraftCitation.draft_id == draft_id, FactCard.status == "CONFIRMED", FactCard.conflict_group.is_(None))
        ).all()
    )
    pending_terms = set(session.scalars(select(FactCard.content).where(FactCard.project_id == draft.project_id, FactCard.status == "PENDING")).all())
    conflict_terms = set(session.scalars(select(FactCard.content).where(FactCard.project_id == draft.project_id, FactCard.status == "CONFLICT")).all())
    reference_texts = list(session.scalars(select(ReferenceCase.raw_text).where(ReferenceCase.project_id == draft.project_id)).all())
    candidates = scan_content(draft.content, sourced_terms, conflict_terms, pending_terms, reference_texts)
    session.execute(delete(QualityIssue).where(QualityIssue.draft_id == draft_id))
    issues = [QualityIssue(draft_id=draft_id, **candidate.__dict__) for candidate in candidates]
    session.add_all(issues)
    session.flush()
    facts = [fact.model_dump() for fact in get_eligible_facts(session, draft.project_id)]
    strategy = session.get(Strategy, draft.strategy_id)
    envelope = provider.check_quality(draft.content, facts, [strategy.method_summary] if strategy else [])
    if envelope.status != "DONE" or envelope.result is None:
        draft.status = "CHECK_INCOMPLETE"
        draft.quality_status = "FAILED"
        session.commit()
        raise QualityCheckIncomplete("检查未完成，请重试后再导出")
    for suggestion in envelope.result.issues:
        policy = "HARD" if suggestion.type in {"PRIVACY_RISK", "FACT_CONFLICT"} else "SOFT"
        issue = QualityIssue(draft_id=draft_id, **suggestion.model_dump(exclude={"auto_fixable"}), status="OPEN", resolution_policy=policy, suggestion="请按提示修改后重新检查" if policy == "HARD" else "可修改或说明接受理由")
        session.add(issue)
        issues.append(issue)
    draft.status = "CHECKED"
    draft.quality_status = "BLOCKED" if any(issue.resolution_policy == "HARD" and issue.status == "OPEN" for issue in issues) else "PASSED"
    session.commit()
    return issues
