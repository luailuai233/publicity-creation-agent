from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import FactCard, FactSource, Material, Project, SourceChunk, Strategy
from workbench.drafts.service import DraftNeedsReview, create_outline, generate_draft


def build_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'drafts.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def seed_selected_strategy(session):
    project = Project(name="编辑器测试")
    session.add(project)
    session.flush()
    material = Material(project_id=project.id, file_name="interview.txt", mime_type="text/plain", category="INTERVIEW")
    session.add(material)
    session.flush()
    chunk = SourceChunk(material_id=material.id, content="活动确认事实来源", paragraph=1)
    session.add(chunk)
    session.flush()
    facts = []
    for index in range(4):
        fact = FactCard(project_id=project.id, type="EVENT", content=f"确认事实 {index + 1}", status="CONFIRMED", confidence=0.9)
        session.add(fact)
        session.flush()
        session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
        facts.append(fact)
    pending = FactCard(project_id=project.id, type="EVENT", content="待确认事实", status="PENDING")
    session.add(pending)
    strategy = Strategy(
        project_id=project.id, name="人物故事型", angle="人物行动", opening="动作切入", structure="行动—变化—回扣",
        fact_ids=[fact.id for fact in facts], method_summary="细节开场", risk="不扩大事实", selected=True,
    )
    session.add(strategy)
    session.commit()
    return project, strategy, facts, pending


def test_outline_has_five_titles_and_draft_uses_only_current_confirmed_facts(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project, strategy, facts, pending = seed_selected_strategy(session)
    provider = MockAIProvider(delay_ms=0)

    outline = create_outline(session, provider, project.id)
    draft = generate_draft(session, provider, project.id, outline.titles[0], outline.outline)

    assert len(outline.titles) == 5
    assert len(outline.outline) >= 3
    assert provider.last_draft_fact_ids == [fact.id for fact in facts]
    assert pending.id not in provider.last_draft_fact_ids
    assert draft.title == outline.titles[0]
    assert {citation.fact_id for citation in draft.citations} == {fact.id for fact in facts}
    assert all(citation.block_id.startswith("block-") for citation in draft.citations)


def test_generation_requires_selected_strategy_and_rechecks_stale_facts(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="没有策略")
    session.add(project)
    session.commit()
    provider = MockAIProvider(delay_ms=0)

    with pytest.raises(DraftNeedsReview, match="先选择一个创作策略"):
        create_outline(session, provider, project.id)

    project, strategy, facts, _pending = seed_selected_strategy(session)
    facts[0].status = "PENDING"
    session.commit()
    with pytest.raises(DraftNeedsReview, match="策略引用的事实已失效"):
        generate_draft(session, provider, project.id, "标题", ["开头", "正文", "结尾"])
