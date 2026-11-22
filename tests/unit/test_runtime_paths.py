from pathlib import Path
import sys
import tomllib

from workbench.runtime_paths import get_runtime_paths


def test_all_writable_paths_stay_inside_project_root() -> None:
    project_root = Path(r"D:\aipm\demo").resolve()

    paths = get_runtime_paths(project_root)

    assert paths.project_root == project_root
    assert paths.pip_cache == project_root / ".runtime" / "pip-cache"
    assert paths.temp == project_root / ".runtime" / "tmp"
    assert paths.playwright_browsers == project_root / ".runtime" / "playwright-browsers"
    assert paths.database == project_root / "storage" / "app.db"
    assert paths.uploads == project_root / "storage" / "projects"
    assert paths.exports == project_root / "exports"
    for writable_path in paths.writable_paths():
        assert writable_path.is_absolute()
        assert writable_path == project_root or project_root in writable_path.parents


def test_project_requires_supported_python_and_wrapper_uses_project_venv() -> None:
    project_root = Path(__file__).resolve().parents[2]
    metadata = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["requires-python"] == ">=3.11,<3.13"
    assert (3, 11) <= sys.version_info[:2] < (3, 13)
    assert project_root.resolve() in Path(sys.executable).resolve().parents

    runtime_script = (project_root / "scripts" / "runtime-env.ps1").read_text(encoding="utf-8")
    test_script = (project_root / "scripts" / "test.ps1").read_text(encoding="utf-8")
    assert "(3, 11) <= sys.version_info[:2] < (3, 13)" in runtime_script
    assert "Assert-WorkbenchVenv" in runtime_script
    assert "[Guid]::NewGuid()" in test_script
    assert "--basetemp" in test_script
