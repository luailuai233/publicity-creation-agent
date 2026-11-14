from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.main import create_app
from workbench.settings import Settings


def test_inspiration_page_keeps_required_three_window_structure(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "灵感布局"}).json()["data"]
        page = client.get(f"/project/{project['id']}/inspiration")
        css = client.get("/static/css/inspiration.css")

    assert page.status_code == 200
    assert page.text.count('class="reference-card') == 3
    assert page.text.count('class="mechanism-card') == 4
    assert page.text.count('class="guidance-group') == 3
    assert page.text.count('class="primary-action') == 1
    assert 'class="inspiration-grid"' in page.text
    assert "grid-template-columns: minmax(0, 1.02fr) minmax(0, 1.07fr) minmax(0, .91fr)" in css.text
    assert "@media (max-width: 1280px)" in css.text
    assert "grid-template-columns" in css.text.split("@media (max-width: 1280px)", 1)[1]
