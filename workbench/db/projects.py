from pathlib import Path
import shutil

from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Project
from workbench.domain.project_schemas import ProjectCreate


class ProjectNotFoundError(LookupError):
    pass


class UnsafeStoragePathError(ValueError):
    pass


def create_project(session: Session, data: ProjectCreate) -> Project:
    project = Project(**data.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def list_projects(session: Session) -> list[Project]:
    statement = select(Project).order_by(Project.sort_order.desc())
    return list(session.scalars(statement).all())


def get_project(session: Session, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)
    return project


def delete_project(session: Session, project_id: str, uploads_root: Path) -> None:
    project = get_project(session, project_id)
    root = uploads_root.resolve()
    project_dir = (root / project.id).resolve()
    if root not in project_dir.parents:
        raise UnsafeStoragePathError(str(project_dir))

    try:
        session.delete(project)
        session.flush()
        if project_dir.exists():
            shutil.rmtree(project_dir)
        session.commit()
    except Exception:
        session.rollback()
        raise
