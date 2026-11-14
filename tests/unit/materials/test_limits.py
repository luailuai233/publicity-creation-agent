import pytest

from workbench.materials.limits import (
    MAX_FILE_BYTES,
    MAX_PROJECT_BYTES,
    MAX_PROJECT_FILES,
    MaterialValidationError,
    validate_upload,
)


@pytest.mark.parametrize(
    ("name", "mime"),
    [
        ("flow.txt", "text/plain"),
        ("brief.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("report.pdf", "application/pdf"),
        ("photo.png", "image/png"),
        ("photo.jpg", "image/jpeg"),
        ("photo.jpeg", "image/jpeg"),
        ("photo.webp", "image/webp"),
    ],
)
def test_supported_file_types_are_accepted(name: str, mime: str) -> None:
    validate_upload(name, mime, MAX_FILE_BYTES, 0, 0)


def test_exact_upload_boundaries_are_accepted() -> None:
    validate_upload("last.txt", "text/plain", MAX_FILE_BYTES, MAX_PROJECT_FILES - 1, MAX_PROJECT_BYTES - MAX_FILE_BYTES)


@pytest.mark.parametrize(
    ("name", "mime", "size", "count", "used", "code"),
    [
        ("too-big.txt", "text/plain", MAX_FILE_BYTES + 1, 0, 0, "FILE_TOO_LARGE"),
        ("extra.txt", "text/plain", 1, MAX_PROJECT_FILES, 0, "TOO_MANY_FILES"),
        ("overflow.txt", "text/plain", 2, 0, MAX_PROJECT_BYTES - 1, "PROJECT_TOO_LARGE"),
        ("script.exe", "application/octet-stream", 1, 0, 0, "UNSUPPORTED_TYPE"),
        ("fake.jpg", "text/plain", 1, 0, 0, "MIME_MISMATCH"),
    ],
)
def test_invalid_uploads_return_specific_codes(name, mime, size, count, used, code) -> None:
    with pytest.raises(MaterialValidationError) as caught:
        validate_upload(name, mime, size, count, used)

    assert caught.value.code == code
