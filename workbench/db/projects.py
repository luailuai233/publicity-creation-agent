from pathlib import Path
import shutil

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, DraftCitation, EventLog, Job, Project, QualityIssue, Strategy, TimelineItem
from workbench.domain.project_schemas import ProjectCreate, ProjectPatch


class ProjectNotFoundError(LookupError):
    pass


class UnsafeStoragePathError(ValueError):
    pass


class ProjectValidationError(ValueError):
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


def update_project(session: Session, project_id: str, patch: ProjectPatch) -> Project:
    project = get_project(session, project_id)
    changes = patch.model_dump(exclude_none=True)
    length_min = changes.get("length_min", project.length_min)
    length_max = changes.get("length_max", project.length_max)
    if length_min > length_max:
        raise ProjectValidationError("最少字数不能大于最多字数")
    if changes:
        for key, value in changes.items():
            setattr(project, key, value)
        project.revision += 1
        from workbench.drafts.service import invalidate_project_checks
        invalidate_project_checks(session, project.id)
        session.commit()
        session.refresh(project)
    return project


def touch_project_inputs(session: Session, project_id: str) -> Project:
    project = get_project(session, project_id)
    project.revision += 1
    from workbench.drafts.service import invalidate_project_checks
    invalidate_project_checks(session, project_id)
    return project


def delete_project(session: Session, project_id: str, uploads_root: Path) -> None:
    project = get_project(session, project_id)
    root = uploads_root.resolve()
    project_dir = (root / project.id).resolve()
    if root not in project_dir.parents:
        raise UnsafeStoragePathError(str(project_dir))

    try:
        draft_ids = list(session.scalars(select(Draft.id).where(Draft.project_id == project_id)).all())
        if draft_ids:
            session.execute(delete(QualityIssue).where(QualityIssue.draft_id.in_(draft_ids)))
            session.execute(delete(DraftCitation).where(DraftCitation.draft_id.in_(draft_ids)))
            session.execute(delete(Draft).where(Draft.id.in_(draft_ids)))
        for model in (Strategy, TimelineItem, Job, EventLog):
            session.execute(delete(model).where(model.project_id == project_id))
        session.delete(project)
        session.flush()
        if project_dir.exists():
            shutil.rmtree(project_dir)
        session.commit()
    except Exception:
        session.rollback()
        raise
