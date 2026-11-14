from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from workbench.settings import Settings


PACKAGE_ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(PACKAGE_ROOT / "templates"))


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    application = FastAPI(title="热点驱动宣传创作工作台")
    application.state.settings = settings or Settings()
    application.mount(
        "/static",
        StaticFiles(directory=str(PACKAGE_ROOT / "static")),
        name="static",
    )

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @application.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="home.html",
            context={"product_name": "热点驱动宣传创作工作台"},
        )

    return application


app = create_app()
