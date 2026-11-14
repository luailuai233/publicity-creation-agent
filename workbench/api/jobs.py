from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.db.models import Job
from workbench.jobs.models import JobRead
from workbench.web.dependencies import get_session


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def show(job_id: str, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if job is None:
        return api_error("JOB_NOT_FOUND", "没有找到这个后台任务", 404)
    return api_response(JobRead.model_validate(job).model_dump(mode="json"))
