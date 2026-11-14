from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import re
from typing import BinaryIO, Optional
import uuid

from workbench.runtime_paths import get_runtime_paths


SAFE_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class UnsafeStoragePathError(ValueError):
    pass


@dataclass(frozen=True)
class StoredFile:
    path: Path
    stored_name: str
    original_name: str
    size_bytes: int


class LocalStorage:
    def __init__(self, uploads_root: Optional[Path] = None) -> None:
        self.uploads_root = (uploads_root or get_runtime_paths().uploads).resolve()

    def _project_root(self, project_id: str) -> Path:
        if not SAFE_PROJECT_ID.fullmatch(project_id) or project_id.upper() in WINDOWS_RESERVED:
            raise UnsafeStoragePathError(project_id)
        target = (self.uploads_root / project_id).resolve()
        if self.uploads_root not in target.parents:
            raise UnsafeStoragePathError(str(target))
        return target

    def save_material_file(self, project_id: str, original_name: str, stream: BinaryIO) -> StoredFile:
        project_root = self._project_root(project_id)
        project_root.mkdir(parents=True, exist_ok=True)
        clean_name = PureWindowsPath(original_name).name or "material"
        clean_name = Path(clean_name).name
        suffix = Path(clean_name).suffix.lower()
        stored_name = f"{uuid.uuid4()}{suffix}"
        target = project_root / stored_name
        payload = stream.read()
        target.write_bytes(payload)
        return StoredFile(target, stored_name, clean_name, len(payload))

    def delete_file(self, path: Path) -> None:
        resolved = path.resolve()
        if self.uploads_root not in resolved.parents:
            raise UnsafeStoragePathError(str(path))
        if resolved.exists():
            resolved.unlink()
