from pathlib import Path
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from workbench.db.base import Base
from workbench.db.models import FactCard, Project, ReferenceCase
from workbench.references.fetcher import ReferenceFetchError
from workbench.references.service import ReferenceCreate, create_reference, delete_reference
from workbench.storage.local import LocalStorage
from workbench.main import create_app
from workbench.settings import Settings


class StubFetcher:
    def __init__(self, text: str | None = None) -> None:
        self.text = text

    def fetch(self, _url: str) -> str:
        if self.text is None:
            raise ReferenceFetchError("blocked")
        return self.text


def build_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reference-inputs.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_text_link_and_screenshot_inputs_remain_outside_fact_table(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="三种案例")
    session.add(project)
    session.commit()

    text = create_reference(session, project.id, ReferenceCreate(input_type="TEXT", raw_text="案例正文"))
    link = create_reference(
        session,
        project.id,
        ReferenceCreate(input_type="LINK", source_url="https://example.com/case"),
        fetcher=StubFetcher("<h1>链接案例</h1>"),
    )
    failed = create_reference(
        session,
        project.id,
        ReferenceCreate(input_type="LINK", source_url="https://example.com/fail"),
        fetcher=StubFetcher(),
    )
    screenshot = create_reference(session, project.id, ReferenceCreate(input_type="SCREENSHOT", raw_path="shot.png"))

    assert text.fetch_status == "NOT_REQUIRED"
    assert link.fetch_status == "DONE" and "链接案例" in link.raw_text
    assert failed.fetch_status == "FAILED" and failed.source_url.endswith("/fail")
    assert screenshot.status == "NEEDS_REVIEW"
    assert session.scalar(select(func.count(FactCard.id))) == 0


def test_deleting_reference_removes_local_original(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="删除原文")
    session.add(project)
    session.commit()
    storage = LocalStorage(tmp_path / "uploads")
    stored = storage.save_material_file(project.id, "shot.png", __import__("io").BytesIO(b"image"))
    reference = create_reference(
        session,
        project.id,
        ReferenceCreate(input_type="SCREENSHOT", raw_path=str(stored.path), raw_text="人工说明"),
    )

    delete_reference(session, storage, reference.id)

    assert session.get(ReferenceCase, reference.id) is None
    assert not stored.path.exists()


def png_bytes() -> bytes:
    payload = BytesIO()
    Image.new("RGB", (24, 24), color=(120, 170, 210)).save(payload, format="PNG")
    return payload.getvalue()


def test_screenshot_upload_saves_inside_project_and_never_accepts_browser_server_path(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "截图案例"}).json()["data"]
        response = client.post(
            f"/api/projects/{project['id']}/references/upload",
            data={"source_label": "公众号截图", "description": "图文以人物行动开篇"},
            files={"file": ("article.png", png_bytes(), "image/png")},
        )

    assert response.status_code == 201
    reference = response.json()["data"]
    stored = Path(reference["raw_path"]).resolve()
    assert stored.exists()
    assert (tmp_path / "storage" / "projects" / project["id"]).resolve() in stored.parents
    assert reference["input_type"] == "SCREENSHOT"
    assert reference["raw_text"] == "图文以人物行动开篇"


def test_screenshot_upload_rejects_non_image_without_writing_file(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "错误截图"}).json()["data"]
        response = client.post(
            f"/api/projects/{project['id']}/references/upload",
            files={"file": ("article.txt", b"not an image", "text/plain")},
        )

    assert response.status_code == 422
    upload_root = tmp_path / "storage" / "projects" / project["id"]
    assert not upload_root.exists() or not list(upload_root.iterdir())
