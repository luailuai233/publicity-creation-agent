from pathlib import Path

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
