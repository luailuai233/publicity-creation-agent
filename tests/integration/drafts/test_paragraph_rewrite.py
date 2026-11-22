from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.ai.envelope import AIEnvelope
from workbench.ai.schemas.draft import ParagraphRewriteResult
from workbench.db.base import Base
from workbench.db.models import Draft, DraftCitation, FactCard, FactSource, Material, Project, SourceChunk, Strategy
from workbench.drafts.service import DraftNeedsReview, rewrite_paragraph


class RewriteProvider:
    def __init__(self, content: str, fact_ids: list[str]):
        self.content = content
        self.fact_ids = fact_ids

    def rewrite_paragraph(self, paragraph, goal, facts, locked_fact_ids):
        assert "另一段" not in paragraph
        return AIEnvelope(result=ParagraphRewriteResult(content=self.content, cited_fact_ids=self.fact_ids))


def seed(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rewrite.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="局部改写")
    session.add(project)
    session.flush()
    fact = FactCard(project_id=project.id, type="NUMBER", content="20人", status="CONFIRMED", confidence=0.9)
    session.add(fact)
    material = Material(project_id=project.id, file_name="source.txt", mime_type="text/plain", parse_status="DONE")
    session.add(material); session.flush()
    chunk = SourceChunk(material_id=material.id, content="现场共有20人参与实验。")
    session.add(chunk); session.flush()
    session.add(FactSource(fact_id=fact.id, source_chunk_id=chunk.id))
    session.flush()
    strategy = Strategy(project_id=project.id, name="人物", angle="行动", opening="现场", structure="时间线", fact_ids=[fact.id], method_summary="细节", selected=True)
    session.add(strategy)
    session.flush()
    draft = Draft(
        project_id=project.id,
        strategy_id=strategy.id,
        title="标题",
        outline=["正文"],
        content="<!-- block:b1 -->\n共有20人参与。\n<!-- block:b2 -->\n另一段保持不变。",
        locked_fact_ids=[fact.id],
        revision=3,
    )
    session.add(draft)
    session.flush()
    session.add(DraftCitation(draft_id=draft.id, fact_id=fact.id, block_id="b1"))
    session.commit()
    return session, draft, fact


def test_rewrite_changes_only_selected_block_and_saves_undo(tmp_path: Path) -> None:
    session, draft, fact = seed(tmp_path)

    rewritten = rewrite_paragraph(session, RewriteProvider("现场共有20人参与实验。", [fact.id]), draft.id, "b1", "更生动", expected_revision=3)

    assert "现场共有20人" in rewritten.content
    assert "另一段保持不变" in rewritten.content
    assert rewritten.undo_snapshot["content"].startswith("<!-- block:b1 -->")


def test_rewrite_rejects_locked_fact_change_and_preserves_original(tmp_path: Path) -> None:
    session, draft, fact = seed(tmp_path)
    original = draft.content

    with pytest.raises(DraftNeedsReview):
        rewrite_paragraph(session, RewriteProvider("现场共有30人参与实验。", [fact.id]), draft.id, "b1", "更生动", expected_revision=3)

    session.refresh(draft)
    assert draft.content == original
