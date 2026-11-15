from pathlib import Path

from workbench.agent.snapshot import build_project_snapshot
from workbench.db.base import Base
from workbench.db.models import (
    Draft,
    FactCard,
    Material,
    QualityIssue,
    ReferenceAnalysis,
    ReferenceCase,
    SourceChunk,
    Strategy,
)
from workbench.db.projects import create_project
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.domain.project_schemas import ProjectCreate


def test_snapshot_reads_current_project_artifacts_from_database(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "snapshot.db")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="开放日"))
        project.goal = "生成开放日长图文"
        project.decisions = {"allow_without_references": False}
        material = Material(project_id=project.id, file_name="流程.txt", mime_type="text/plain", parse_status="DONE")
        session.add(material)
        session.flush()
        session.add(SourceChunk(material_id=material.id, content="活动于九点开始"))
        session.add_all(
            [
                FactCard(project_id=project.id, type="TIME", content="九点开始", status="CONFIRMED", confidence=0.9),
                FactCard(project_id=project.id, type="NUMBER", content="30 人", status="CONFLICT", confidence=0.8, conflict_group="number-1"),
            ]
        )
        analyzed = ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="案例", selected=True, status="DONE")
        pending = ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="待分析", selected=True, status="PENDING")
        session.add_all([analyzed, pending])
        session.flush()
        session.add(ReferenceAnalysis(reference_id=analyzed.id, hook="细节", transferable=["克制开头"]))
        strategies = [
            Strategy(project_id=project.id, name=f"策略 {index}", angle="角度", opening="开头", structure="结构", selected=index == 1)
            for index in range(1, 4)
        ]
        session.add_all(strategies)
        session.flush()
        draft = Draft(project_id=project.id, strategy_id=strategies[0].id, title="标题", status="DRAFT", quality_status="STALE")
        session.add(draft)
        session.flush()
        session.add(QualityIssue(draft_id=draft.id, type="MISSING_SOURCE", severity="HIGH", message="缺少来源"))
        session.commit()

        result = build_project_snapshot(session, project.id)

    assert result.goal == "生成开放日长图文"
    assert result.source_chunk_count == 1
    assert result.eligible_fact_types == ["TIME"]
    assert result.conflict_groups == ["number-1"]
    assert result.selected_reference_count == 2
    assert result.usable_reference_count == 1
    assert result.unanalyzed_reference_ids == [pending.id]
    assert result.strategy_count == 3
    assert result.selected_strategy_id == strategies[0].id
    assert result.draft_id == draft.id
    assert result.quality_status == "STALE"
    assert result.blocking_issue_count == 1
