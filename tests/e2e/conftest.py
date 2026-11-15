from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.main import create_app
from workbench.settings import Settings


@pytest.fixture
def demo_client(tmp_path: Path):
    root = tmp_path / "demo-runtime"
    app = create_app(Settings(project_root=root, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        yield client, root
