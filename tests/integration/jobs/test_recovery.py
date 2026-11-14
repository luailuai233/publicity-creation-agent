from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import Job, Material, Project
from workbench.jobs.recovery import recover_stale_jobs
from workbench.jobs.runner import run_material_job


def build_sessions(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'jobs.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_recovery_marks_processing_jobs_failed_and_retryable(tmp_path: Path) -> None:
    sessions = build_sessions(tmp_path)
    with sessions() as session:
        project = Project(name="恢复测试")
        session.add(project)
        session.flush()
        job = Job(project_id=project.id, type="PARSE_MATERIAL", status="PROCESSING", progress=45, started_at=datetime.utcnow())
        session.add(job)
        session.commit()
        job_id = job.id

    with sessions() as session:
        changed = recover_stale_jobs(session)
        recovered = session.get(Job, job_id)

    assert changed == 1
    assert recovered.status == "FAILED"
    assert recovered.retryable is True
    assert recovered.error_code == "INTERRUPTED_BY_RESTART"


def test_one_parse_failure_does_not_rollback_successful_sibling(tmp_path: Path) -> None:
    sessions = build_sessions(tmp_path)
    good_path = tmp_path / "good.txt"
    bad_path = tmp_path / "bad.png"
    good_path.write_text("活动于 10 月 18 日举行。", encoding="utf-8")
    bad_path.write_bytes(b"not-an-image")

    with sessions() as session:
        project = Project(name="独立任务测试")
        session.add(project)
        session.flush()
        good = Material(project_id=project.id, file_name="good.txt", mime_type="text/plain", path=str(good_path))
        bad = Material(project_id=project.id, file_name="bad.png", mime_type="image/png", path=str(bad_path))
        session.add_all([good, bad])
        session.flush()
        good_job = Job(project_id=project.id, material_id=good.id, type="PARSE_MATERIAL")
        bad_job = Job(project_id=project.id, material_id=bad.id, type="PARSE_MATERIAL")
        session.add_all([good_job, bad_job])
        session.commit()
        good_job_id, bad_job_id = good_job.id, bad_job.id

    run_material_job(sessions, good_job_id)
    run_material_job(sessions, bad_job_id)

    with sessions() as session:
        assert session.get(Job, good_job_id).status == "DONE"
        assert session.get(Job, bad_job_id).status == "FAILED"
        assert session.get(Material, good.id).parse_status == "DONE"
        assert session.get(Material, bad.id).parse_status == "FAILED"
