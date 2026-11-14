from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from workbench.ai.provider import AIProvider
from workbench.db.models import ReferenceAnalysis, ReferenceCase, Strategy
from workbench.facts.eligibility import get_eligible_facts
from workbench.strategies.difference import validate_strategy_set


class StrategyNeedsReview(RuntimeError):
    pass


def generate_strategies(session: Session, provider: AIProvider, project_id: str) -> list[Strategy]:
    facts = get_eligible_facts(session, project_id)
    if len(facts) < 3:
        raise StrategyNeedsReview("至少确认 3 条事实后才能生成策略")
    transferable = session.scalars(
        select(ReferenceAnalysis.transferable)
        .join(ReferenceCase, ReferenceCase.id == ReferenceAnalysis.reference_id)
        .where(ReferenceCase.project_id == project_id, ReferenceCase.selected.is_(True))
    ).all()
    method_summaries = [item for group in transferable for item in (group or [])]
    envelope = provider.generate_strategies(
        [fact.model_dump() for fact in facts], method_summaries, project_name=project_id
    )
    if envelope.status != "DONE" or envelope.result is None:
        raise StrategyNeedsReview("策略模拟生成未完成，已保留上一版")
    difference = validate_strategy_set(envelope.result.strategies)
    if not difference.valid:
        raise StrategyNeedsReview("；".join(difference.errors))
    session.execute(delete(Strategy).where(Strategy.project_id == project_id))
    persisted = []
    for item in envelope.result.strategies:
        strategy = Strategy(project_id=project_id, **item.model_dump(), selected=False, is_demo=True)
        session.add(strategy)
        persisted.append(strategy)
    session.commit()
    for strategy in persisted:
        session.refresh(strategy)
    return persisted


def select_strategy(session: Session, strategy_id: str, settings: dict) -> Strategy:
    strategy = session.get(Strategy, strategy_id)
    if strategy is None:
        raise LookupError(strategy_id)
    session.execute(update(Strategy).where(Strategy.project_id == strategy.project_id).values(selected=False))
    strategy.selected = True
    strategy.settings = settings
    session.commit()
    session.refresh(strategy)
    return strategy
