from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import Material, Project, ReferenceCase


def test_material_and_reference_case_are_stored_in_separate_tables(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'isolation.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    with sessions() as session:
        project = Project(name="隔离测试")
        session.add(project)
        session.flush()
        session.add(Material(project_id=project.id, file_name="活动流程.txt", mime_type="text/plain"))
        session.add(ReferenceCase(project_id=project.id, input_type="TEXT", raw_text="参考写法"))
        session.commit()

    with sessions() as session:
        materials = session.scalars(select(Material)).all()
        references = session.scalars(select(ReferenceCase)).all()

    assert [item.file_name for item in materials] == ["活动流程.txt"]
    assert [item.raw_text for item in references] == ["参考写法"]
    assert Material.__tablename__ == "materials"
    assert ReferenceCase.__tablename__ == "reference_cases"
