from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Project
from workbench.db.projects import create_project
from workbench.domain.project_schemas import ProjectCreate


DEMO_PROJECT_NAME = "Demo · 秋日公益市集宣传"


def ensure_demo_project(session: Session) -> Project:
    existing = session.scalar(select(Project).where(Project.is_demo.is_(True)))
    if existing is not None:
        return existing
    return create_project(session, ProjectCreate(name=DEMO_PROJECT_NAME, is_demo=True))
