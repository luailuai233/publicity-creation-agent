from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.main import create_app
from workbench.settings import Settings


def build_client(tmp_path: Path) -> TestClient:
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    return TestClient(app)


def test_homepage_has_fixed_retro_shell_and_one_primary_action(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        page = client.get("/")
        css = client.get("/static/css/app.css")

    assert page.status_code == 200
    assert page.text.count('class="primary-action') == 1
    assert 'class="system-topbar"' in page.text
    assert 'class="desktop-dock"' in page.text
    assert 'class="bottom-taskbar"' in page.text
    assert "--topbar-height: 52px" in css.text
    assert "--dock-width: 116px" in css.text
    assert "--taskbar-height: 44px" in css.text
    assert ":focus-visible" in css.text
    assert "prefers-reduced-motion" in css.text


def test_recent_project_has_explicit_delete_confirmation(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        created = client.post("/api/projects", json={"name": "可删除任务"}).json()["data"]
        page = client.get("/")

    assert created["name"] == "可删除任务"
    assert 'hx-confirm="删除后项目素材也会一并清理，确定继续吗？"' in page.text
    assert "可删除任务" in page.text
