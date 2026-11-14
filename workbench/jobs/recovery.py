from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Job


def recover_stale_jobs(session: Session) -> int:
    jobs = list(session.scalars(select(Job).where(Job.status == "PROCESSING")).all())
    for job in jobs:
        job.status = "FAILED"
        job.error_code = "INTERRUPTED_BY_RESTART"
        job.retryable = True
        job.stage = "服务重启，等待重试"
        job.ended_at = datetime.utcnow()
    session.commit()
    return len(jobs)
