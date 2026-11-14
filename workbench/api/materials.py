from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.db.models import Job, Material
from workbench.db.projects import ProjectNotFoundError, get_project
from workbench.jobs.models import JobCreate, JobRead
from workbench.jobs.repository import enqueue_job
from workbench.jobs.runner import run_material_job
from workbench.materials.limits import MaterialValidationError
from workbench.materials.service import create_file_material, delete_material, serialize_material
from workbench.storage.local import LocalStorage
from workbench.web.dependencies import get_session


router = APIRouter(tags=["materials"])


class MaterialPatch(BaseModel):
    category: Optional[str] = None
    parsed_text: Optional[str] = None


@router.get("/api/projects/{project_id}/materials")
def index(project_id: str, session: Session = Depends(get_session)):
    materials = session.scalars(select(Material).where(Material.project_id == project_id).order_by(Material.created_at)).all()
    return api_response([serialize_material(item) for item in materials])


@router.post("/api/projects/{project_id}/materials", status_code=201)
async def create(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    files: Optional[List[UploadFile]] = File(default=None),
    pasted_text: Optional[str] = Form(default=None),
    session: Session = Depends(get_session),
):
    try:
        get_project(session, project_id)
    except ProjectNotFoundError:
        return api_error("PROJECT_NOT_FOUND", "没有找到这个创作任务", 404)
    storage = LocalStorage(request.app.state.settings.paths.uploads)
    incoming = list(files or [])
    if pasted_text and pasted_text.strip():
        from starlette.datastructures import UploadFile as StarletteUploadFile
        from io import BytesIO

        incoming.append(StarletteUploadFile(filename="粘贴文本.txt", file=BytesIO(pasted_text.encode("utf-8")), headers={"content-type": "text/plain"}))
    results = []
    try:
        for upload in incoming:
            payload = await upload.read()
            material, job = create_file_material(session, storage, project_id, upload.filename or "material", upload.content_type or "application/octet-stream", payload)
            background_tasks.add_task(run_material_job, request.app.state.session_factory, job.id)
            results.append({"material": serialize_material(material), "job": JobRead.model_validate(job).model_dump(mode="json")})
    except MaterialValidationError as error:
        return api_error(error.code, error.message, 400)
    return api_response(results, status_code=201)


@router.patch("/api/materials/{material_id}")
def update(material_id: str, patch: MaterialPatch, session: Session = Depends(get_session)):
    material = session.get(Material, material_id)
    if material is None:
        return api_error("MATERIAL_NOT_FOUND", "没有找到这个素材", 404)
    for key, value in patch.model_dump(exclude_none=True).items():
        setattr(material, key, value)
    session.commit()
    session.refresh(material)
    return api_response(serialize_material(material))


@router.post("/api/materials/{material_id}/retry")
def retry(material_id: str, request: Request, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    material = session.get(Material, material_id)
    if material is None:
        return api_error("MATERIAL_NOT_FOUND", "没有找到这个素材", 404)
    material.parse_status = "QUEUED"
    session.commit()
    job = enqueue_job(session, JobCreate(project_id=material.project_id, material_id=material.id, type="PARSE_MATERIAL"))
    background_tasks.add_task(run_material_job, request.app.state.session_factory, job.id)
    return api_response(JobRead.model_validate(job).model_dump(mode="json"), status_code=202)


@router.delete("/api/materials/{material_id}")
def destroy(material_id: str, request: Request, session: Session = Depends(get_session)):
    material = session.get(Material, material_id)
    if material is None:
        return api_error("MATERIAL_NOT_FOUND", "没有找到这个素材", 404)
    delete_material(session, LocalStorage(request.app.state.settings.paths.uploads), material_id)
    return api_response({"deleted": material_id})
