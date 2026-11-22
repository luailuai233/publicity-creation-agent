from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import Draft, Project, QualityIssue, ReferenceCase, Strategy
from workbench.exports.plain_text import write_plain_text_export


def test_plain_text_defaults_to_body_only_and_can_include_notes(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'plain.db'}"); Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="中文项目/../安全"); session.add(project); session.flush()
    strategy = Strategy(project_id=project.id, name="策略", angle="角度", opening="开头", structure="结构", fact_ids=[], method_summary="人物视角", risk="", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, content="<!-- block:b1 -->\n# 标题\n\n正文内容", status="CHECKED", quality_status="PASSED")
    session.add(draft); session.flush()
    session.add(QualityIssue(draft_id=draft.id, type="TONE_RISK", severity="LOW", block_id="b1", message="语气待确认", status="ACCEPTED", resolution_policy="SOFT", resolution_note="已人工复核"))
    session.add(ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="绝不能泄漏的参考原文", source_label="案例")); session.commit()

    body_path = write_plain_text_export(session, draft.id, tmp_path / "exports", confirm_high=True)
    body = body_path.read_text(encoding="utf-8")
    notes_path = write_plain_text_export(session, draft.id, tmp_path / "exports-notes", confirm_high=True, include_notes=True)
    notes = notes_path.read_text(encoding="utf-8")

    assert body == "标题\n\n正文内容\n"
    assert "创作说明" in notes and "待确认清单" in notes
    assert "语气待确认" not in notes
    assert "block:b1" not in notes and "绝不能泄漏的参考原文" not in notes
    assert body_path.parent == (tmp_path / "exports").resolve()
