from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from workbench.api.projects import router as projects_api_router
from workbench.api.responses import api_error
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.settings import Settings
from workbench.web.page_routes import router as page_router


PACKAGE_ROOT = Path(__file__).resolve().parent


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    application = FastAPI(title="热点驱动宣传创作工作台")
    application.state.settings = settings or Settings()
    application.state.engine = create_sqlite_engine(application.state.settings.paths.database)
    application.state.session_factory = create_session_factory(application.state.engine)
    application.mount(
        "/static",
        StaticFiles(directory=str(PACKAGE_ROOT / "static")),
        name="static",
    )

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        fields = [".".join(str(part) for part in error["loc"]) for error in exc.errors()]
        return api_error("VALIDATION_ERROR", "请检查输入内容", 422, fields)

    application.include_router(projects_api_router)
    application.include_router(page_router)

    return application


app = create_app()
