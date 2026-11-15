from pathlib import Path
import os
import socket
import subprocess
import sys
import time

import httpx
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


@pytest.fixture
def live_server(tmp_path: Path):
    root = tmp_path / "live-runtime"
    app = create_app(Settings(project_root=root, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    app.state.engine.dispose()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
    env = os.environ.copy(); env["WORKBENCH_ROOT"] = str(root); env["MOCK_AI_DELAY_MS"] = "0"
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "workbench.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=str(Path(__file__).resolve().parents[2]), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(url + "/health", timeout=0.2, trust_env=False).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:
        process.terminate(); output, _ = process.communicate(timeout=10)
        raise RuntimeError(f"Uvicorn test server failed to start:\n{output}")
    try:
        yield url, root
    finally:
        process.terminate(); process.wait(timeout=10)
