from datetime import datetime

from sqlalchemy.orm import sessionmaker

from workbench.db.models import Job, Material, SourceChunk
from workbench.materials.parsers import parse_path


def run_material_job(session_factory: sessionmaker, job_id: str) -> None:
    with session_factory() as session:
        job = session.get(Job, job_id)
        if job is None or job.material_id is None:
            return
        material = session.get(Material, job.material_id)
        job.status = "PROCESSING"
        job.progress = 20
        job.stage = "正在解析素材"
        job.started_at = datetime.utcnow()
        material.parse_status = "PROCESSING"
        session.commit()

    try:
        result = parse_path(material_path(material.path), material.mime_type)
        with session_factory() as session:
            job = session.get(Job, job_id)
            material = session.get(Material, job.material_id)
            material.parsed_text = result.text
            material.summary = result.summary
            material.category = result.category
            material.parse_status = result.status
            session.add(SourceChunk(material_id=material.id, content=result.text, paragraph=1))
            job.status = "DONE"
            job.progress = 100
            job.stage = "解析完成"
            job.retryable = False
            job.ended_at = datetime.utcnow()
            session.commit()
    except Exception:
        with session_factory() as session:
            job = session.get(Job, job_id)
            material = session.get(Material, job.material_id) if job and job.material_id else None
            if job:
                job.status = "FAILED"
                job.progress = 100
                job.stage = "解析失败"
                job.error_code = "PARSE_FAILED"
                job.retryable = True
                job.ended_at = datetime.utcnow()
            if material:
                material.parse_status = "FAILED"
            session.commit()


def material_path(value: str):
    from pathlib import Path

    return Path(value)
