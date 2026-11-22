import asyncio
import logging
import time
from uuid import uuid4
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from workbench.ai.factory import create_ai_provider
from workbench.agent.recovery import recover_agent_runs
from workbench.agent.runner import AgentRunner
from workbench.agent.tools.registry import build_default_registry
from workbench.api.agent_runs import router as agent_runs_api_router
from workbench.api.references import router as references_api_router
from workbench.api.strategies import router as strategies_api_router
from workbench.api.drafts import router as drafts_api_router
from workbench.api.quality import router as quality_api_router
from workbench.api.exports import router as exports_api_router
from workbench.api.projects import router as projects_api_router
from workbench.api.jobs import router as jobs_api_router
from workbench.api.materials import router as materials_api_router
from workbench.api.facts import router as facts_api_router
from workbench.api.responses import api_error
from workbench.api.demo import router as demo_api_router
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.settings import Settings
from workbench.web.page_routes import router as page_router
from workbench.web.material_routes import router as material_page_router
from workbench.web.inspiration_routes import router as inspiration_page_router
from workbench.web.strategy_routes import router as strategy_page_router
from workbench.web.editor_routes import router as editor_page_router
from workbench.web.export_routes import router as export_page_router
from workbench.jobs.recovery import recover_stale_jobs
from workbench.logging import log_event


PACKAGE_ROOT = Path(__file__).resolve().parent


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    effective_settings = settings or Settings()
    engine = create_sqlite_engine(effective_settings.paths.database)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        with session_factory() as session:
            recover_stale_jobs(session)
            recovered_run_ids = recover_agent_runs(session)
        application.state.agent_tasks = set()
        for run_id in recovered_run_ids:
            task = asyncio.create_task(asyncio.to_thread(application.state.agent_runner.run, run_id))
            application.state.agent_tasks.add(task)
            task.add_done_callback(application.state.agent_tasks.discard)
        yield

    application = FastAPI(title="热点驱动宣传创作工作台", lifespan=lifespan)
    application.state.settings = effective_settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.ai_provider = create_ai_provider(effective_settings)
    application.state.agent_registry = build_default_registry()
    application.state.agent_runner = AgentRunner(
        session_factory,
        application.state.agent_registry,
        provider=application.state.ai_provider,
    )

    @application.middleware("http")
    async def public_site_safety(request: Request, call_next):
        if effective_settings.app_env == "production":
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    too_large = int(content_length) > effective_settings.max_request_body_bytes
                except ValueError:
                    too_large = True
                if too_large:
                    response = api_error("REQUEST_TOO_LARGE", "请求内容超过服务器限制", 413)
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            return response
        return await call_next(request)

    @application.middleware("http")
    async def request_trace(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log_event(logging.getLogger("workbench.request"), "request", request_id=request_id, method=request.method, path=request.url.path, status="ERROR", duration_ms=int((time.perf_counter() - started) * 1000))
            raise
        response.headers["X-Request-ID"] = request_id
        log_event(logging.getLogger("workbench.request"), "request", request_id=request_id, method=request.method, path=request.url.path, status=response.status_code, duration_ms=int((time.perf_counter() - started) * 1000))
        return response
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
    application.include_router(agent_runs_api_router)
    application.include_router(demo_api_router)
    application.include_router(materials_api_router)
    application.include_router(facts_api_router)
    application.include_router(references_api_router)
    application.include_router(strategies_api_router)
    application.include_router(drafts_api_router)
    application.include_router(quality_api_router)
    application.include_router(exports_api_router)
    application.include_router(jobs_api_router)
    application.include_router(page_router)
    application.include_router(material_page_router)
    application.include_router(inspiration_page_router)
    application.include_router(strategy_page_router)
    application.include_router(editor_page_router)
    application.include_router(export_page_router)

    return application


app = create_app()
