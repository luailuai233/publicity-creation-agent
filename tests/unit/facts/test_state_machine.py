from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import FactCard, FactSource, Material, Project, SourceChunk
from workbench.facts.eligibility import get_eligible_facts
from workbench.facts.service import FactTransitionError, auto_confirm_safe_facts, resolve_conflict, update_fact
from workbench.facts.schemas import ConflictResolution, FactPatch


def build_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'facts.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def add_fact_with_source(session, fact_type="EVENT", category="FLOW", status="PENDING", content="举行公益市集"):
    project = Project(name="事实测试")
    session.add(project)
    session.flush()
    material = Material(project_id=project.id, file_name="source.txt", mime_type="text/plain", category=category)
    session.add(material)
    session.flush()
    chunk = SourceChunk(material_id=material.id, content="来源原文", page=2, paragraph=3)
    fact = FactCard(project_id=project.id, type=fact_type, content=content, status=status, confidence=0.9)
    session.add_all([chunk, fact])
    session.flush()
    session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
    session.commit()
    return project, fact


def test_pending_fact_can_be_confirmed_or_invalidated(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    _, fact = add_fact_with_source(session)

    confirmed = update_fact(session, fact.id, FactPatch(status="CONFIRMED"))
    assert confirmed.status == "CONFIRMED"

    invalidated = update_fact(session, fact.id, FactPatch(status="INVALID"))
    assert invalidated.status == "INVALID"


def test_quote_requires_interview_or_speech_source(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    _, quote = add_fact_with_source(session, fact_type="QUOTE", category="FLOW", content="我们一起成长")

    with pytest.raises(FactTransitionError, match="采访或发言稿"):
        update_fact(session, quote.id, FactPatch(status="CONFIRMED"))


def test_quote_accepts_an_interview_filename_when_legacy_category_is_other(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="采访来源")
    session.add(project)
    session.flush()
    material = Material(
        project_id=project.id,
        file_name="02_采访记录.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        category="OTHER",
    )
    session.add(material)
    session.flush()
    chunk = SourceChunk(material_id=material.id, content="受访者表示：“正式地点尚未公布”。", paragraph=8)
    quote = FactCard(project_id=project.id, type="QUOTE", content="正式地点尚未公布", status="PENDING", confidence=0.9)
    session.add_all([chunk, quote])
    session.flush()
    session.add(FactSource(fact_id=quote.id, source_chunk_id=chunk.id))
    session.commit()

    confirmed = update_fact(session, quote.id, FactPatch(status="CONFIRMED"))

    assert confirmed.status == "CONFIRMED"


def test_conflicts_are_ineligible_until_manually_resolved(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project, first = add_fact_with_source(session, status="CONFLICT", content="活动时间为 9:00")
    first.project_id = project.id
    first.conflict_group = "time-1"
    second = FactCard(project_id=project.id, type="TIME", content="活动时间为 9:30", status="CONFLICT", conflict_group="time-1")
    session.add(second)
    session.commit()

    assert get_eligible_facts(session, project.id) == []

    chosen = resolve_conflict(session, "time-1", ConflictResolution(fact_id=first.id))
    eligible = get_eligible_facts(session, project.id)

    assert chosen.id == first.id
    assert chosen.status == "CONFIRMED"
    assert [fact.id for fact in eligible] == [first.id]
    assert session.get(FactCard, second.id).status == "INVALID"


@pytest.mark.parametrize("fact_type", ["PERSON", "ROLE"])
def test_identity_fact_types_are_not_auto_confirmed(tmp_path: Path, fact_type: str) -> None:
    session = build_session(tmp_path)
    project, fact = add_fact_with_source(session, fact_type=fact_type)

    assert auto_confirm_safe_facts(session, project.id) == []
    assert fact.status == "PENDING"
