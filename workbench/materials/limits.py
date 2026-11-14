from pathlib import Path


MIB = 1024 * 1024
MAX_FILE_BYTES = 20 * MIB
MAX_PROJECT_FILES = 30
MAX_PROJECT_BYTES = 200 * MIB

ACCEPTED_TYPES = {
    ".txt": {"text/plain"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}


class MaterialValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def validate_upload(file_name: str, mime_type: str, size_bytes: int, current_count: int, current_bytes: int) -> None:
    suffix = Path(file_name).suffix.lower()
    if suffix not in ACCEPTED_TYPES:
        raise MaterialValidationError("UNSUPPORTED_TYPE", "仅支持 DOCX、PDF、TXT、PNG、JPG/JPEG 和 WEBP")
    if mime_type not in ACCEPTED_TYPES[suffix]:
        raise MaterialValidationError("MIME_MISMATCH", "文件扩展名与内容类型不一致")
    if size_bytes > MAX_FILE_BYTES:
        raise MaterialValidationError("FILE_TOO_LARGE", "单个文件不能超过 20 MB")
    if current_count >= MAX_PROJECT_FILES:
        raise MaterialValidationError("TOO_MANY_FILES", "每个项目最多上传 30 个文件")
    if current_bytes + size_bytes > MAX_PROJECT_BYTES:
        raise MaterialValidationError("PROJECT_TOO_LARGE", "项目素材总量不能超过 200 MB")
