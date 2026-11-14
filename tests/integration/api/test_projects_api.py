from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.main import create_app
from workbench.settings import Settings


def build_client(tmp_path: Path) -> TestClient:
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    return TestClient(app)


def test_project_api_create_list_get_and_delete(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        first_response = client.post("/api/projects", json={"name": "第一个任务"})
        second_response = client.post("/api/projects", json={"name": "第二个任务"})
        first = first_response.json()["data"]
        second = second_response.json()["data"]

        listing = client.get("/api/projects").json()
        fetched = client.get(f"/api/projects/{first['id']}").json()
        deleted = client.delete(f"/api/projects/{first['id']}").json()
        missing = client.get(f"/api/projects/{first['id']}")

    assert first_response.status_code == 201
    assert first["audience"] == "校园活动关注者"
    assert first["tone"] == "真实、温暖、克制"
    assert [item["id"] for item in listing["data"]] == [second["id"], first["id"]]
    assert fetched["data"]["name"] == "第一个任务"
    assert deleted["data"] == {"deleted": first["id"]}
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    for payload in (listing, fetched, deleted):
        assert set(payload) == {"data", "error", "requestId"}


def test_project_api_validation_error_is_actionable_chinese(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        response = client.post("/api/projects", json={"name": ""})

    payload = response.json()
    assert response.status_code == 422
    assert payload["data"] is None
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "请检查输入内容"
    assert payload["requestId"]
