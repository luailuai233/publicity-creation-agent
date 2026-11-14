from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from workbench.db.models import Material
from workbench.jobs.models import JobCreate
from workbench.jobs.repository import enqueue_job
from workbench.materials.limits import validate_upload
from workbench.storage.local import LocalStorage


def project_usage(session: Session, project_id: str) -> tuple[int, int]:
    count, total = session.execute(
        select(func.count(Material.id), func.coalesce(func.sum(Material.size_bytes), 0)).where(Material.project_id == project_id)
    ).one()
    return int(count), int(total)


def create_file_material(session: Session, storage: LocalStorage, project_id: str, file_name: str, mime_type: str, payload: bytes):
    count, used = project_usage(session, project_id)
    validate_upload(file_name, mime_type, len(payload), count, used)
    stored = storage.save_material_file(project_id, file_name, BytesIO(payload))
    material = Material(
        project_id=project_id,
        file_name=stored.original_name,
        mime_type=mime_type,
        path=str(stored.path),
        size_bytes=stored.size_bytes,
    )
    session.add(material)
    session.commit()
    session.refresh(material)
    job = enqueue_job(session, JobCreate(project_id=project_id, material_id=material.id, type="PARSE_MATERIAL"))
    return material, job


def serialize_material(material: Material) -> dict:
    return {
        "id": material.id,
        "project_id": material.project_id,
        "file_name": material.file_name,
        "mime_type": material.mime_type,
        "category": material.category,
        "parse_status": material.parse_status,
        "summary": material.summary,
        "parsed_text": material.parsed_text,
        "path": material.path,
        "size_bytes": material.size_bytes,
    }
