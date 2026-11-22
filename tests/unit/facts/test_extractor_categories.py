from pathlib import Path

from sqlalchemy import select

from workbench.db.base import Base
from workbench.db.models import FactCard, Material, Project, SourceChunk
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.facts.extractor import extract_fact_candidates


def test_quote_extraction_ignores_titles_and_keeps_attributed_interview_words(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "quote-extraction.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = Project(name="引语分类")
        session.add(project)
        session.flush()
        flow = Material(project_id=project.id, file_name="01_活动流程.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", category="OTHER")
        interview = Material(project_id=project.id, file_name="02_采访记录.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", category="OTHER")
        session.add_all([flow, interview])
        session.flush()
        session.add_all(
            [
                SourceChunk(material_id=flow.id, content="“支教团迎新日”活动流程与基础信息", paragraph=1),
                SourceChunk(material_id=interview.id, content="受访者表示：“正式服务地点和出发时间尚未公布”。", paragraph=8),
            ]
        )
        session.commit()

        extract_fact_candidates(session, project.id)

        quotes = list(session.scalars(select(FactCard).where(FactCard.project_id == project.id, FactCard.type == "QUOTE")).all())
        session.refresh(flow)
        session.refresh(interview)

    assert [fact.content for fact in quotes] == ["正式服务地点和出发时间尚未公布"]
    assert flow.category == "FLOW"
    assert interview.category == "INTERVIEW"
