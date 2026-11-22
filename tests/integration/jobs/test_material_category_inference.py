from pathlib import Path

from docx import Document

from workbench.db.base import Base
from workbench.db.models import Job, Material, Project
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.jobs.runner import run_material_job


def test_docx_job_infers_interview_category_from_the_original_filename(tmp_path: Path) -> None:
    path = tmp_path / "stored.docx"
    document = Document()
    document.add_paragraph("受访者表示：正式服务地点尚未公布。")
    document.save(path)
    engine = create_sqlite_engine(tmp_path / "category.db")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        project = Project(name="素材分类")
        session.add(project)
        session.flush()
        material = Material(
            project_id=project.id,
            file_name="02_采访记录.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            path=str(path),
        )
        session.add(material)
        session.flush()
        job = Job(project_id=project.id, material_id=material.id, type="PARSE_MATERIAL")
        session.add(job)
        session.commit()
        material_id = material.id
        job_id = job.id

    run_material_job(factory, job_id)

    with factory() as session:
        persisted = session.get(Material, material_id)
        assert persisted.category == "INTERVIEW"
