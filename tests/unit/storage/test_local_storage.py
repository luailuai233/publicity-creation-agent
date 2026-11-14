from io import BytesIO
from pathlib import Path

import pytest

from workbench.storage.local import LocalStorage, UnsafeStoragePathError


def test_storage_uses_generated_names_and_keeps_files_inside_project(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path / "projects")

    first = storage.save_material_file("project-1", "..\\..\\agenda.txt", BytesIO(b"first"))
    second = storage.save_material_file("project-1", "agenda.txt", BytesIO(b"second"))

    project_root = (tmp_path / "projects" / "project-1").resolve()
    assert first.path.parent == project_root
    assert second.path.parent == project_root
    assert first.path.name != second.path.name
    assert first.path.suffix == ".txt"
    assert first.original_name == "agenda.txt"
    assert first.path.read_bytes() == b"first"
    assert second.path.read_bytes() == b"second"


@pytest.mark.parametrize("project_id", ["../escape", "D:/escape", "project\\escape", "CON"])
def test_storage_rejects_unsafe_project_identifiers(tmp_path: Path, project_id: str) -> None:
    storage = LocalStorage(tmp_path / "projects")

    with pytest.raises(UnsafeStoragePathError):
        storage.save_material_file(project_id, "safe.txt", BytesIO(b"data"))
