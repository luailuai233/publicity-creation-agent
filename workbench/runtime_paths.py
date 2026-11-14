from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class RuntimePaths:
    project_root: Path
    runtime_root: Path
    pip_cache: Path
    pycache: Path
    python_user: Path
    temp: Path
    playwright_browsers: Path
    database: Path
    uploads: Path
    exports: Path
    test_results: Path

    def writable_paths(self) -> Iterable[Path]:
        return (
            self.runtime_root,
            self.pip_cache,
            self.pycache,
            self.python_user,
            self.temp,
            self.playwright_browsers,
            self.database,
            self.uploads,
            self.exports,
            self.test_results,
        )


def get_runtime_paths(root: Optional[Path] = None) -> RuntimePaths:
    configured_root = root or Path(os.environ.get("WORKBENCH_ROOT", Path.cwd()))
    project_root = configured_root.resolve()
    runtime_root = project_root / ".runtime"
    return RuntimePaths(
        project_root=project_root,
        runtime_root=runtime_root,
        pip_cache=runtime_root / "pip-cache",
        pycache=runtime_root / "pycache",
        python_user=runtime_root / "python-user",
        temp=runtime_root / "tmp",
        playwright_browsers=runtime_root / "playwright-browsers",
        database=project_root / "storage" / "app.db",
        uploads=project_root / "storage" / "projects",
        exports=project_root / "exports",
        test_results=project_root / "test-results",
    )
