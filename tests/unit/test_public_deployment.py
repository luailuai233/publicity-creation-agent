from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.main import create_app
from workbench.settings import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_render_style_environment_uses_one_runtime_root(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "render-runtime"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WORKBENCH_ROOT", str(runtime_root))
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "26214400")

    settings = Settings()

    assert settings.app_env == "production"
    assert settings.paths.project_root == runtime_root.resolve()
    assert settings.paths.database == runtime_root.resolve() / "storage" / "app.db"
    assert settings.max_request_body_bytes == 26_214_400


def test_production_health_has_security_headers_and_rejects_large_request(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, app_env="production", max_request_body_bytes=1024)
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)

    with TestClient(app) as client:
        health = client.get("/health")
        oversized = client.post("/api/projects", content=b"x" * 1025, headers={"content-type": "application/json"})

    assert health.status_code == 200
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["referrer-policy"] == "no-referrer"
    assert health.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_container_and_render_blueprint_follow_single_instance_contract() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    startup = (PROJECT_ROOT / "scripts" / "container-start.sh").read_text(encoding="utf-8")
    blueprint = (PROJECT_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "requirements-prod.lock" in dockerfile
    assert "COPY data ./data" in dockerfile
    assert 'CMD ["sh", "scripts/container-start.sh"]' in dockerfile
    assert "python -m alembic upgrade head" in startup
    assert 'sqlite:///${WORKBENCH_ROOT}/storage/app.db' in startup
    assert '--port "${PORT}" --workers 1' in startup
    assert "plan: free" in blueprint
    assert "healthCheckPath: /health" in blueprint
    assert "WORKBENCH_ROOT" in blueprint and "/tmp/workbench" in blueprint
    assert "AI_PROVIDER" in blueprint and "mock" in blueprint
