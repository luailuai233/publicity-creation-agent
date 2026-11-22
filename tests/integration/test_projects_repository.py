from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.projects import (
    ProjectNotFoundError,
    create_project,
    delete_project,
    get_project,
    list_projects,
)
from workbench.domain.project_schemas import ProjectCreate


@pytest.fixture()
def session_factory(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_project_defaults_persist_across_sessions(session_factory) -> None:
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="秋日公益市集"))
        project_id = project.id

    with session_factory() as session:
        restored = get_project(session, project_id)

    assert restored.name == "秋日公益市集"
    assert restored.audience == "校园活动关注者"
    assert restored.tone == "真实、温暖、克制"
    assert restored.length_min == 1200
    assert restored.length_max == 1600
    assert restored.status == "MATERIALS"
    assert restored.is_demo is False


def test_list_projects_returns_newest_first(session_factory) -> None:
    with session_factory() as session:
        first = create_project(session, ProjectCreate(name="第一个任务"))
        second = create_project(session, ProjectCreate(name="第二个任务"))

        projects = list_projects(session)

    assert [project.id for project in projects] == [second.id, first.id]


def test_unknown_project_raises_domain_error(session_factory) -> None:
    with session_factory() as session:
        with pytest.raises(ProjectNotFoundError):
            get_project(session, "missing-project")


def test_delete_project_removes_database_row_and_storage(session_factory, tmp_path: Path) -> None:
    uploads_root = tmp_path / "storage" / "projects"
    with session_factory() as session:
        project = create_project(session, ProjectCreate(name="待删除任务"))
        project_dir = uploads_root / project.id
        project_dir.mkdir(parents=True)
        (project_dir / "material.txt").write_text("demo", encoding="utf-8")

        delete_project(session, project.id, uploads_root)

        assert project_dir.exists() is False
        with pytest.raises(ProjectNotFoundError):
            get_project(session, project.id)
