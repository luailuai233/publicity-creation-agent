from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from workbench.ai.faults import FaultInjector
from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import FactCard, Project, ReferenceAnalysis, ReferenceCase, Strategy
from workbench.strategies.service import StrategyNeedsReview, generate_strategies, select_strategy


def build_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'strategies.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def seed_project(session, confirmed=4):
    project = Project(name="策略生成")
    session.add(project)
    session.flush()
    statuses = ["CONFIRMED"] * confirmed + ["PENDING", "CONFLICT"]
    for index, status in enumerate(statuses):
        fact_type = "LOCATION" if index == 1 else "EVENT"
        session.add(FactCard(project_id=project.id, type=fact_type, content=f"事实 {index + 1}", status=status, confidence=0.9, conflict_group="g" if status == "CONFLICT" else None))
    reference = ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="案例原文绝不能进入策略", selected=True, status="DONE")
    session.add(reference)
    session.flush()
    session.add(ReferenceAnalysis(reference_id=reference.id, hook="细节开头", emotion="克制递进", structure="行动后回扣", image_role="场景证据", transferable=["细节开头"], avoid=["照搬原句"]))
    session.commit()
    return project


def test_generation_uses_only_confirmed_facts_and_method_summaries(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = seed_project(session)

    strategies = generate_strategies(session, MockAIProvider(delay_ms=0), project.id)

    confirmed_ids = set(session.scalars(select(FactCard.id).where(FactCard.status == "CONFIRMED")).all())
    assert [item.name for item in strategies] == ["人物故事型", "反差成长型", "现场纪实型"]
    assert all(set(item.fact_ids) <= confirmed_ids for item in strategies)
    assert len({tuple(item.fact_ids) for item in strategies}) == 3
    assert all("案例原文绝不能进入策略" not in item.method_summary for item in strategies)

    selected = select_strategy(session, strategies[1].id, {"tone": "克制", "length": "1200-1600"})
    assert selected.selected is True
    assert selected.settings == {"tone": "克制", "length": "1200-1600"}
    assert session.scalar(select(func.count(Strategy.id)).where(Strategy.selected.is_(True))) == 1


def test_insufficient_facts_returns_needs_review(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = seed_project(session, confirmed=1)

    with pytest.raises(StrategyNeedsReview, match="活动事实和一条具体细节"):
        generate_strategies(session, MockAIProvider(delay_ms=0), project.id)


def test_schema_retry_and_failed_regeneration_preserve_previous_set(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = seed_project(session)
    retrying = MockAIProvider(delay_ms=0, faults=FaultInjector({"strategy": ["schema_error"]}))
    initial = generate_strategies(session, retrying, project.id)
    assert retrying.last_strategy_envelope.retries == 1
    previous_ids = [item.id for item in initial]

    failing = MockAIProvider(delay_ms=0, faults=FaultInjector({"strategy": ["schema_error", "schema_error"]}))
    with pytest.raises(StrategyNeedsReview):
        generate_strategies(session, failing, project.id)

    assert list(session.scalars(select(Strategy.id).where(Strategy.project_id == project.id)).all()) == previous_ids


def test_real_provider_strategy_provenance_is_not_demo(tmp_path: Path) -> None:
    class RealStrategyProviderStub:
        def generate_strategies(self, facts, method_summaries, project_name):
            envelope = MockAIProvider(delay_ms=0).generate_strategies(facts, method_summaries, project_name)
            return envelope.model_copy(update={"provider": "real-provider-stub", "is_demo": False})

    session = build_session(tmp_path)
    project = seed_project(session)

    strategies = generate_strategies(session, RealStrategyProviderStub(), project.id)

    assert all(strategy.is_demo is False for strategy in strategies)
