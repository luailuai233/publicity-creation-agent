from pathlib import Path

from sqlalchemy import select

from workbench.agent.repository import create_run
from workbench.agent.runner import AgentRunner
from workbench.agent.tools.registry import build_default_registry
from workbench.ai.envelope import AIEnvelope
from workbench.ai.faults import FaultInjector
from workbench.ai.mock_provider import MockAIProvider
from workbench.ai.schemas.quality import QualityResult, QualitySuggestion
from workbench.db.base import Base
from workbench.db.models import AgentRun, AgentStep, Draft, Strategy
from workbench.db.session import create_session_factory, create_sqlite_engine
from tests.integration.agent.test_tools import seed_ready_project


def test_one_start_runs_reference_strategy_content_and_quality_to_completion(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "autonomous.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    provider = MockAIProvider(delay_ms=0)
    with factory() as session:
        project, _reference, _facts = seed_ready_project(session)
        run = create_run(session, project.id, project.goal)
        run_id = run.id

    AgentRunner(factory, build_default_registry(), provider=provider).run(run_id)

    with factory() as session:
        run = session.get(AgentRun, run_id)
        tool_names = list(session.scalars(select(AgentStep.tool_name).where(AgentStep.run_id == run_id).order_by(AgentStep.sequence)).all())
        strategies = list(session.scalars(select(Strategy).where(Strategy.project_id == project.id)).all())
        draft = session.scalar(select(Draft).where(Draft.project_id == project.id, Draft.is_current.is_(True)))

    assert run.status == "COMPLETED", (run.waiting_reason, tool_names, run.error_code)
    assert tool_names == ["analyze_references", "plan_strategies", "generate_content", "check_quality"]
    assert len(strategies) == 3
    assert sum(strategy.selected for strategy in strategies) == 1
    assert draft is not None
    assert draft.quality_status == "PASSED"
    assert run.tool_call_count == 4


class AutoFixProvider(MockAIProvider):
    def check_quality(self, content: str, facts: list[dict], method_summaries: list[str]):
        return AIEnvelope[QualityResult](
            result=QualityResult(
                issues=[
                    QualitySuggestion(
                        type="SIMILAR_EXPRESSION",
                        severity="MEDIUM",
                        block_id="document",
                        message="表达可进一步去同质化",
                        auto_fixable=True,
                    )
                ]
            ),
            provider=self.provider_name,
        )


def test_agent_auto_revises_at_most_once_then_completes(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "revision.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    provider = AutoFixProvider(delay_ms=0)
    with factory() as session:
        project, _reference, _facts = seed_ready_project(session)
        run = create_run(session, project.id, project.goal)
        run_id = run.id

    AgentRunner(factory, build_default_registry(), provider=provider).run(run_id)

    with factory() as session:
        run = session.get(AgentRun, run_id)
        tool_names = list(session.scalars(select(AgentStep.tool_name).where(AgentStep.run_id == run_id).order_by(AgentStep.sequence)).all())
        contents = list(session.scalars(select(Draft.content).where(Draft.project_id == project.id).order_by(Draft.version)).all())
    assert run.status == "COMPLETED"
    assert run.revision_count == 1
    assert tool_names.count("generate_content") == 2
    assert tool_names.count("check_quality") == 2
    assert len(contents) == 2
    assert contents[0] != contents[1]


def test_failed_reference_analysis_waits_for_user_instead_of_failing(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "reference-failure.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    provider = MockAIProvider(delay_ms=0, faults=FaultInjector({"reference": ["timeout", "timeout"]}))
    with factory() as session:
        project, _reference, _facts = seed_ready_project(session)
        run = create_run(session, project.id, project.goal)
        run_id = run.id

    AgentRunner(factory, build_default_registry(), provider=provider).run(run_id)

    with factory() as session:
        run = session.get(AgentRun, run_id)
    assert run.status == "WAITING_USER"
    assert run.waiting_reason == "MISSING_REFERENCE"
