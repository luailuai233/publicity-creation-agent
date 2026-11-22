from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.ai.faults import FaultInjector
from workbench.ai.mock_provider import MockAIProvider
from workbench.db.base import Base
from workbench.db.models import Draft, Project, Strategy
from workbench.quality.service import QualityCheckIncomplete, run_quality_check


def test_failed_supplemental_check_marks_draft_incomplete_not_passed(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'quality.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = Project(name="检查失败")
    session.add(project); session.flush()
    strategy = Strategy(project_id=project.id, name="现场纪实型", angle="现场", opening="声音", structure="时间线", fact_ids=[], method_summary="细节", risk="克制", selected=True)
    session.add(strategy); session.flush()
    draft = Draft(project_id=project.id, strategy_id=strategy.id, title="待检查稿", outline=[], content="<!-- block:block-1 -->\n现场记录。", version=1)
    session.add(draft); session.commit()
    provider = MockAIProvider(delay_ms=0, faults=FaultInjector({"quality": ["schema_error", "schema_error"]}))

    with pytest.raises(QualityCheckIncomplete):
        run_quality_check(session, provider, draft.id)

    assert session.get(Draft, draft.id).status == "CHECK_INCOMPLETE"
    assert not any(issue.status == "RESOLVED" for issue in session.get(Draft, draft.id).quality_issues)
