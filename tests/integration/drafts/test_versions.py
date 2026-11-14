from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from workbench.ai.faults import FaultInjector
from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import Draft, FactCard, FactSource, Material, Project, SourceChunk, Strategy
from workbench.drafts.service import DraftNeedsReview, generate_draft, save_draft
from workbench.drafts.schemas import DraftPatch


def seed(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'versions.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="版本测试")
    session.add(project); session.flush()
    material = Material(project_id=project.id, file_name="source.txt", mime_type="text/plain", category="FLOW")
    session.add(material); session.flush()
    chunk = SourceChunk(material_id=material.id, content="来源")
    session.add(chunk); session.flush()
    facts = []
    for index in range(3):
        fact = FactCard(project_id=project.id, type="EVENT", content=f"事实 {index}", status="CONFIRMED")
        session.add(fact); session.flush(); session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id)); facts.append(fact)
    strategy = Strategy(project_id=project.id, name="现场纪实型", angle="现场", opening="声音", structure="时间线", fact_ids=[f.id for f in facts], method_summary="细节", risk="克制", selected=True)
    session.add(strategy); session.commit()
    return session, project


def test_each_generation_creates_version_and_save_updates_current_only(tmp_path: Path) -> None:
    session, project = seed(tmp_path)
    provider = MockAIProvider(delay_ms=0)

    first = generate_draft(session, provider, project.id, "第一版", ["开头", "正文", "结尾"])
    second = generate_draft(session, provider, project.id, "第二版", ["现场", "人物", "回扣"])
    saved = save_draft(session, second.id, DraftPatch(content=second.content + "\n\n人工补充。"))

    assert first.version == 1
    assert session.get(Draft, first.id).is_current is False
    assert second.version == 2
    assert saved.is_current is True
    assert saved.content.endswith("人工补充。")


def test_failed_generation_preserves_existing_draft(tmp_path: Path) -> None:
    session, project = seed(tmp_path)
    existing = generate_draft(session, MockAIProvider(delay_ms=0), project.id, "保留稿", ["一", "二", "三"])
    failing = MockAIProvider(delay_ms=0, faults=FaultInjector({"draft": ["schema_error", "schema_error"]}))

    with pytest.raises(DraftNeedsReview):
        generate_draft(session, failing, project.id, "失败稿", ["一", "二", "三"])

    assert session.scalar(select(func.count(Draft.id))) == 1
    assert session.get(Draft, existing.id).title == "保留稿"
    assert session.get(Draft, existing.id).is_current is True
