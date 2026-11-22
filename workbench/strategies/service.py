from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from workbench.ai.provider import AIProvider
from workbench.db.models import Draft, Project, ReferenceAnalysis, ReferenceCase, Strategy
from workbench.facts.eligibility import get_eligible_facts
from workbench.strategies.difference import validate_strategy_set
from workbench.agent.planner import has_minimum_fact_set


class StrategyNeedsReview(RuntimeError):
    pass


def generate_strategies(session: Session, provider: AIProvider, project_id: str) -> list[Strategy]:
    facts = get_eligible_facts(session, project_id)
    if not has_minimum_fact_set([fact.type for fact in facts]):
        raise StrategyNeedsReview("至少需要一条活动事实和一条具体细节事实")
    transferable = session.scalars(
        select(ReferenceAnalysis.transferable)
        .join(ReferenceCase, ReferenceCase.id == ReferenceAnalysis.reference_id)
        .where(ReferenceCase.project_id == project_id, ReferenceCase.selected.is_(True))
    ).all()
    method_summaries = [item for group in transferable for item in (group or [])]
    if not method_summaries:
        raise StrategyNeedsReview("至少需要一个有效参考案例和方法卡")
    project = session.get(Project, project_id)
    project_brief = f"{project.name}｜目标：{project.goal}｜受众：{project.audience}｜语气：{project.tone}｜篇幅：{project.length_min}-{project.length_max}字"
    envelope = provider.generate_strategies(
        [fact.model_dump() for fact in facts], method_summaries, project_name=project_brief
    )
    if envelope.status != "DONE" or envelope.result is None:
        raise StrategyNeedsReview("策略模拟生成未完成，已保留上一版")
    difference = validate_strategy_set(envelope.result.strategies)
    if not difference.valid:
        raise StrategyNeedsReview("；".join(difference.errors))
    eligible_ids = {fact.id for fact in facts}
    for item in envelope.result.strategies:
        if set(item.fact_ids) - eligible_ids:
            raise StrategyNeedsReview("策略引用了当前项目之外或未确认的事实")
        if not any(method in item.method_summary for method in method_summaries):
            raise StrategyNeedsReview("策略方法来源不属于当前已选案例")
    used_ids = list(session.scalars(select(Draft.strategy_id).where(Draft.project_id == project_id)).all())
    session.execute(update(Strategy).where(Strategy.project_id == project_id).values(selected=False))
    removable = delete(Strategy).where(Strategy.project_id == project_id)
    if used_ids:
        removable = removable.where(Strategy.id.not_in(used_ids))
    session.execute(removable)
    persisted = []
    for index, item in enumerate(envelope.result.strategies):
        strategy = Strategy(project_id=project_id, **item.model_dump(), selected=False, is_demo=envelope.is_demo)
        session.add(strategy)
        persisted.append(strategy)
    session.flush()
    decisions = dict(project.decisions or {})
    decisions["recommended_strategy_id"] = persisted[envelope.result.recommended_index].id
    project.decisions = decisions
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
    session.execute(update(Draft).where(Draft.project_id == strategy.project_id, Draft.is_current.is_(True)).values(status="STALE", quality_status="STALE"))
    project = session.get(Project, strategy.project_id)
    decisions = dict(project.decisions or {})
    decisions["strategy_override_id"] = strategy.id
    project.decisions = decisions
    project.revision += 1
    session.commit()
    session.refresh(strategy)
    return strategy
