from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.main import create_app
from workbench.settings import Settings


def build_client(tmp_path: Path) -> TestClient:
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    return TestClient(app)


def test_material_upload_jobs_edit_delete_and_page_layout(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        project = client.post("/api/projects", json={"name": "素材 API"}).json()["data"]
        response = client.post(
            f"/api/projects/{project['id']}/materials",
            files=[
                ("files", ("flow.txt", "10 月 18 日举行公益市集".encode("utf-8"), "text/plain")),
                ("files", ("broken.png", b"not-an-image", "image/png")),
            ],
        )
        uploaded = response.json()["data"]
        good, bad = uploaded
        good_job = client.get(f"/api/jobs/{good['job']['id']}").json()["data"]
        bad_job = client.get(f"/api/jobs/{bad['job']['id']}").json()["data"]
        patched = client.patch(
            f"/api/materials/{good['material']['id']}",
            json={"category": "FLOW", "parsed_text": "人工修正文本"},
        ).json()["data"]
        page = client.get(f"/project/{project['id']}/materials")
        deleted = client.delete(f"/api/materials/{good['material']['id']}")

    assert response.status_code == 201
    assert good_job["status"] == "DONE"
    assert bad_job["status"] == "FAILED"
    assert bad_job["retryable"] is True
    assert patched["category"] == "FLOW"
    assert patched["parsed_text"] == "人工修正文本"
    assert page.status_code == 200
    assert 'class="materials-tree"' in page.text
    assert 'class="materials-list"' in page.text
    assert 'class="material-preview"' in page.text
    assert "1500" in client.get("/static/js/materials.js").text
    assert deleted.status_code == 200
    assert Path(good["material"]["path"]).exists() is False
