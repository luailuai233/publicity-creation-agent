from sqlalchemy.orm import Session

from workbench.db.models import Job
from workbench.jobs.models import JobCreate


def enqueue_job(session: Session, data: JobCreate) -> Job:
    job = Job(**data.model_dump(), status="QUEUED", progress=0, stage="等待处理")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
