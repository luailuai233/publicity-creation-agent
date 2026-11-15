from pathlib import Path

from sqlalchemy import func, select

from workbench.agent.tools.base import AgentToolContext
from workbench.agent.tools.content import ContentToolInput
from workbench.agent.tools.registry import build_default_registry
from workbench.agent.tools.strategies import StrategyToolInput
from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import Draft, FactCard, FactSource, Material, Project, QualityIssue, ReferenceAnalysis, ReferenceCase, SourceChunk, Strategy
from workbench.facts.extractor import extract_fact_candidates
from workbench.facts.schemas import FactPatch
from workbench.facts.service import update_fact
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


def test_contradictory_dates_and_counts_are_grouped_as_conflicts(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "conflicts.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = Project(name="冲突项目")
        session.add(project); session.flush()
        material = Material(project_id=project.id, file_name="facts.txt", mime_type="text/plain", category="INTERVIEW", parse_status="DONE")
        session.add(material); session.flush()
        session.add_all([SourceChunk(material_id=material.id, content="10月18日共有36人参加。"), SourceChunk(material_id=material.id, content="10月19日共有42人参加。")])
        session.commit()
        facts = extract_fact_candidates(session, project.id)
    conflicted = [fact for fact in facts if fact.type in {"TIME", "NUMBER"}]
    assert len(conflicted) == 4
    assert all(fact.status == "CONFLICT" and fact.conflict_group for fact in conflicted)


def test_fact_edit_invalidates_quality_and_bumps_project_revision(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "invalidation.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project, _reference, facts = seed_ready_project(session)
        strategy = Strategy(project_id=project.id, name="现场", angle="现场", opening="声音", structure="时间线", fact_ids=[fact.id for fact in facts], method_summary="", risk="", selected=True)
        session.add(strategy); session.flush()
        draft = Draft(project_id=project.id, strategy_id=strategy.id, title="稿件", outline=[], content="正文", version=1, status="CHECKED", quality_status="PASSED", is_current=True)
        session.add(draft); session.commit()
        before = project.revision
        update_fact(session, facts[0].id, FactPatch(content="修订后的事实"))
        session.refresh(project); session.refresh(draft)
    assert project.revision == before + 1
    assert draft.quality_status == "STALE"


def test_project_goal_reaches_strategy_generation(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "goal.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project, _reference, _facts = seed_ready_project(session)
        context = AgentToolContext(run_id="run", project_id=project.id, session=session, provider=MockAIProvider(delay_ms=0))
        build_default_registry().get("analyze_references").execute(context, build_default_registry().get("analyze_references").input_model(project_id=project.id))
        strategies = build_default_registry().get("plan_strategies").execute(context, StrategyToolInput(project_id=project.id))
        persisted = list(session.scalars(select(Strategy).where(Strategy.project_id == project.id)).all())
    assert strategies.result_ref
    assert any(project.goal in strategy.angle for strategy in persisted)


def test_material_tool_uses_paths_and_isolates_bad_files(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "materials.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    good_path = tmp_path / "good.txt"
    good_path.write_text("可解析资料", encoding="utf-8")
    with factory() as session:
        project = Project(name="资料解析")
        session.add(project); session.flush()
        good = Material(project_id=project.id, file_name="good.txt", path=str(good_path), mime_type="text/plain", parse_status="QUEUED")
        bad = Material(project_id=project.id, file_name="missing.txt", path=str(tmp_path / "missing.txt"), mime_type="text/plain", parse_status="QUEUED")
        session.add_all([good, bad]); session.commit()
        context = AgentToolContext(run_id="run", project_id=project.id, session=session, provider=MockAIProvider(delay_ms=0))
        tool = build_default_registry().get("parse_materials")
        result = tool.execute(context, tool.input_model(project_id=project.id))
        session.refresh(good); session.refresh(bad)
        chunks = list(session.scalars(select(SourceChunk).where(SourceChunk.material_id == good.id)).all())
    assert good.parse_status == "DONE"
    assert bad.parse_status == "FAILED"
    assert len(chunks) == 1
    assert "1 份失败" in result.summary

