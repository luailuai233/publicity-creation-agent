from pathlib import Path

from sqlalchemy import func, select

from workbench.agent.tools.base import AgentToolContext
from workbench.agent.tools.content import ContentToolInput
from workbench.agent.tools.registry import build_default_registry
from workbench.agent.tools.strategies import StrategyToolInput
from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import Draft, FactCard, FactSource, Material, Project, QualityIssue, ReferenceAnalysis, ReferenceCase, SourceChunk, Strategy
from workbench.db.session import create_session_factory, create_sqlite_engine


def seed_ready_project(session):
    project = Project(name="Agent 工具项目", goal="生成真实温暖的长图文")
    session.add(project)
    session.flush()
    material = Material(project_id=project.id, file_name="facts.txt", mime_type="text/plain", category="INTERVIEW", parse_status="DONE")
    session.add(material)
    session.flush()
    chunk = SourceChunk(material_id=material.id, content="10 月 18 日活动现场共有 36 名志愿者参与。")
    session.add(chunk)
    session.flush()
    facts = []
    for index, fact_type in enumerate(("TIME", "EVENT", "LOCATION", "NUMBER"), start=1):
        fact = FactCard(project_id=project.id, type=fact_type, content=f"确认事实 {index}", status="CONFIRMED", confidence=0.9)
        session.add(fact)
        session.flush()
        session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
        facts.append(fact)
    reference = ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="参考案例原文不可进入事实库", status="PENDING", selected=True)
    session.add(reference)
    session.commit()
    return project, reference, facts


def test_default_registry_contains_only_six_whitelisted_tools(tmp_path: Path) -> None:
    registry = build_default_registry()

    assert registry.names() == (
        "parse_materials",
        "validate_facts",
        "analyze_references",
        "plan_strategies",
        "generate_content",
        "check_quality",
    )


def test_reference_analysis_isolated_and_strategy_tool_auto_selects_recommendation(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "tools.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    provider = MockAIProvider(delay_ms=0)
    registry = build_default_registry()
    with factory() as session:
        project, reference, _facts = seed_ready_project(session)
        context = AgentToolContext(run_id="run", project_id=project.id, session=session, provider=provider)
        registry.get("analyze_references").execute(context, registry.get("analyze_references").input_model(project_id=project.id))
        before_facts = session.scalar(select(func.count()).select_from(FactCard))
        registry.get("plan_strategies").execute(context, StrategyToolInput(project_id=project.id))
        after_facts = session.scalar(select(func.count()).select_from(FactCard))
        selected = session.scalar(select(Strategy).where(Strategy.project_id == project.id, Strategy.selected.is_(True)))
        analysis_count = session.scalar(select(func.count()).select_from(ReferenceAnalysis).where(ReferenceAnalysis.reference_id == reference.id))
        session.refresh(project)

    assert before_facts == after_facts == 4
    assert analysis_count == 1
    assert selected is not None
    assert project.decisions["recommended_strategy_id"] == selected.id
    assert "参考案例原文不可进入事实库" not in selected.method_summary


def test_content_tool_uses_recommended_title_and_quality_tool_sets_gate(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "content-tools.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    provider = MockAIProvider(delay_ms=0)
    registry = build_default_registry()
    with factory() as session:
        project, _reference, _facts = seed_ready_project(session)
        context = AgentToolContext(run_id="run", project_id=project.id, session=session, provider=provider)
        registry.get("analyze_references").execute(context, registry.get("analyze_references").input_model(project_id=project.id))
        registry.get("plan_strategies").execute(context, StrategyToolInput(project_id=project.id))
        registry.get("generate_content").execute(context, ContentToolInput(project_id=project.id, mode="initial"))
        draft = session.scalar(select(Draft).where(Draft.project_id == project.id, Draft.is_current.is_(True)))
        registry.get("check_quality").execute(context, registry.get("check_quality").input_model(project_id=project.id))
        session.refresh(draft)
        session.refresh(project)
        citation_count = len(draft.citations)
        selected = session.get(Strategy, draft.strategy_id)
        issues = list(session.scalars(select(QualityIssue).where(QualityIssue.draft_id == draft.id)).all())

    assert draft.title == project.decisions["recommended_title"]
    assert citation_count == len(selected.fact_ids)
    assert draft.quality_status == "PASSED", [(issue.type, issue.message) for issue in issues]

