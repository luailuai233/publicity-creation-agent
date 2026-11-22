from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import FactCard, ReferenceCase
from workbench.demo.seed import load_demo_dataset, reset_demo_project


def test_desensitized_sample_loads_conflict_low_confidence_and_separate_references(tmp_path: Path) -> None:
    dataset = load_demo_dataset()
    assert dataset["license"] == "CC0-1.0"
    assert dataset["synthetic"] is True
    assert dataset["expected"]["time_conflict"] is True
    assert dataset["expected"]["low_confidence_input"] is True
    assert dataset["expected"]["similar_expression"] is True

    engine = create_engine(f"sqlite:///{tmp_path / 'sample.db'}"); Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    project = reset_demo_project(session, tmp_path / "uploads")
    facts = list(session.scalars(select(FactCard).where(FactCard.project_id == project.id)).all())
    references = list(session.scalars(select(ReferenceCase).where(ReferenceCase.project_id == project.id)).all())

    assert len([fact for fact in facts if fact.conflict_group == "demo-start-time"]) == 2
    assert any(fact.confidence < 0.7 for fact in facts)
    assert len(references) == 3
    assert not any(reference.raw_text == fact.content for reference in references for fact in facts)
