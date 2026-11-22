from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import Draft, Project, QualityIssue, ReferenceCase, Strategy
from workbench.exports.markdown import ExportBlocked, write_markdown_export


def test_markdown_export_requires_recorded_soft_confirmation_and_stays_inside_exports(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'export.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="安全导出")
    session.add(project); session.flush()
    strategy = Strategy(project_id=project.id, name="人物故事型", angle="人物", opening="动作", structure="变化", fact_ids=[], method_summary="方法摘要", risk="风险", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, title="真实发生的温暖", outline=["开头", "正文"], content="# 真实发生的温暖\n\n活动如期举行。", version=1, status="CHECKED")
    session.add(draft); session.flush()
    issue = QualityIssue(draft_id=draft.id, type="SIMILAR_EXPRESSION", severity="MEDIUM", block_id="block-1", message="表达相似", status="OPEN", resolution_policy="SOFT")
    session.add(issue)
    session.add(ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="绝不能出现在导出里的参考案例原文", source_label="案例"))
    session.commit()
    export_root = tmp_path / "exports"

    with pytest.raises(ExportBlocked, match="软风险"):
        write_markdown_export(session, draft.id, export_root, confirm_high=False)

    issue.status = "ACCEPTED"; issue.resolution_note = "   "; session.commit()
    with pytest.raises(ExportBlocked, match="软风险"):
        write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True)
    issue.resolution_note = "已人工复核"; session.commit()
    path = write_markdown_export(session, draft.id, export_root, confirm_high=False)
    text = path.read_text(encoding="utf-8")

    assert path.parent == export_root.resolve()
    assert path.suffix == ".md"
    assert "真实发生的温暖" in text
    assert "活动如期举行" in text
    assert draft.id not in text
    assert project.id not in text
    assert "mock-structured-v1" not in text
    assert "prompt" not in text.lower()
    assert "绝不能出现在导出里的参考案例原文" not in text


def test_export_is_blocked_when_check_is_incomplete(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'incomplete.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="未完成检查")
    session.add(project); session.flush()
    strategy = Strategy(project_id=project.id, name="现场", angle="现场", opening="声音", structure="时间线", fact_ids=[], method_summary="", risk="", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, title="稿件", outline=[], content="正文", version=1, status="CHECK_INCOMPLETE")
    session.add(draft); session.commit()

    with pytest.raises(ExportBlocked, match="检查未完成"):
        write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True)


def test_export_never_allows_factual_blockers_even_with_confirmation(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'blocked.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="事实阻断")
    session.add(project); session.flush()
    strategy = Strategy(project_id=project.id, name="现场", angle="现场", opening="声音", structure="时间线", fact_ids=[], method_summary="", risk="", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, title="稿件", outline=[], content="正文", version=1, status="CHECKED", quality_status="BLOCKED")
    session.add(draft); session.flush()
    session.add(QualityIssue(draft_id=draft.id, type="FACT_CONFLICT", severity="HIGH", block_id="document", message="事实冲突", status="OPEN"))
    session.commit()

    with pytest.raises(ExportBlocked, match="硬风险"):
        write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True)


@pytest.mark.parametrize("issue_type", ["PRIVACY_RISK", "FACT_CONFLICT", "MISSING_SOURCE"])
def test_export_never_allows_open_hard_issue(tmp_path: Path, issue_type: str) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / f'{issue_type}.db'}"); Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="硬风险"); session.add(project); session.flush()
    strategy = Strategy(project_id=project.id, name="策略", angle="角度", opening="开头", structure="结构", fact_ids=[], method_summary="", risk="", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, content="正文", status="CHECKED", quality_status="PASSED")
    session.add(draft); session.flush()
    session.add(QualityIssue(draft_id=draft.id, type=issue_type, severity="HIGH", block_id="document", message="硬风险", status="OPEN", resolution_policy="HARD")); session.commit()

    with pytest.raises(ExportBlocked, match="硬风险"):
        write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True)


def test_export_requires_every_soft_issue_to_be_resolved_or_accepted_with_note(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'soft.db'}"); Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="软风险"); session.add(project); session.flush()
    strategy = Strategy(project_id=project.id, name="策略", angle="角度", opening="开头", structure="结构", fact_ids=[], method_summary="", risk="", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, content="正文", status="CHECKED", quality_status="PASSED")
    session.add(draft); session.flush()
    issue = QualityIssue(draft_id=draft.id, type="SIMILAR_EXPRESSION", severity="MEDIUM", block_id="document", message="相似", status="OPEN", resolution_policy="SOFT")
    session.add(issue); session.commit()

    with pytest.raises(ExportBlocked, match="软风险"):
        write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True)
    issue.status = "ACCEPTED"; issue.resolution_note = "已人工复核"; session.commit()
    assert write_markdown_export(session, draft.id, tmp_path / "exports", confirm_high=True).exists()
