from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from workbench.api.responses import api_error, api_response
from workbench.db.projects import ProjectNotFoundError, ProjectValidationError, create_project, delete_project, get_project, list_projects, update_project
from workbench.domain.project_schemas import ProjectCreate, ProjectPatch, ProjectRead
from workbench.web.dependencies import get_session


router = APIRouter(prefix="/api/projects", tags=["projects"])


def serialize(project) -> dict:
    return ProjectRead.model_validate(project).model_dump(mode="json")


@router.get("")
def index(session: Session = Depends(get_session)):
    return api_response([serialize(project) for project in list_projects(session)])


@router.post("", status_code=201)
def create(data: ProjectCreate, session: Session = Depends(get_session)):
    return api_response(serialize(create_project(session, data)), status_code=201)


@router.get("/{project_id}")
def show(project_id: str, session: Session = Depends(get_session)):
    try:
        return api_response(serialize(get_project(session, project_id)))
    except ProjectNotFoundError:
        return api_error("PROJECT_NOT_FOUND", "没有找到这个创作任务", 404)


@router.patch("/{project_id}")
def update(project_id: str, patch: ProjectPatch, session: Session = Depends(get_session)):
    try:
        return api_response(serialize(update_project(session, project_id, patch)))
    except ProjectNotFoundError:
        return api_error("PROJECT_NOT_FOUND", "没有找到这个创作任务", 404)
    except ProjectValidationError as error:
        return api_error("VALIDATION_ERROR", str(error), 422)


@router.delete("/{project_id}")
def destroy(project_id: str, request: Request, session: Session = Depends(get_session)):
    try:
        delete_project(session, project_id, request.app.state.settings.paths.uploads)
    except ProjectNotFoundError:
        return api_error("PROJECT_NOT_FOUND", "没有找到这个创作任务", 404)
    return api_response({"deleted": project_id})
