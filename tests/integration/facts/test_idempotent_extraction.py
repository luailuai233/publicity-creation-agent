from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import FactCard, FactSource, Material, Project, SourceChunk
from workbench.facts.extractor import extract_fact_candidates


def build_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'facts.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_repeated_and_multi_source_extraction_merges_fact_and_sources(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="事实去重")
    session.add(project)
    session.flush()
    for name in ("a.txt", "b.txt"):
        material = Material(project_id=project.id, file_name=name, mime_type="text/plain", parse_status="DONE")
        session.add(material)
        session.flush()
        session.add(SourceChunk(material_id=material.id, content="共有 20 人参与"))
    session.commit()

    extract_fact_candidates(session, project.id)
    extract_fact_candidates(session, project.id)

    fact = session.scalar(select(FactCard).where(FactCard.project_id == project.id, FactCard.type == "NUMBER"))
    assert fact.normalized_value == "20人"
    assert session.scalar(select(func.count(FactCard.id)).where(FactCard.project_id == project.id)) == 1
    assert session.scalar(select(func.count(FactSource.source_chunk_id)).where(FactSource.fact_id == fact.id)) == 2
