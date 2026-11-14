from dataclasses import dataclass
from pathlib import Path

from docx import Document
from PIL import Image
from pypdf import PdfReader


@dataclass(frozen=True)
class ParseResult:
    text: str
    summary: str
    category: str
    status: str = "DONE"
    is_demo: bool = False


def _summary(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:180] + ("…" if len(compact) > 180 else "")


def parse_path(path: Path, mime_type: str) -> ParseResult:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        return ParseResult(text=text, summary=_summary(text), category="NOTE")
    if suffix == ".docx":
        text = "\n".join(paragraph.text for paragraph in Document(path).paragraphs if paragraph.text.strip())
        return ParseResult(text=text, summary=_summary(text), category="OTHER")
    if suffix == ".pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        return ParseResult(text=text, summary=_summary(text), category="OTHER", status="DONE" if text.strip() else "NEEDS_REVIEW")
    if mime_type.startswith("image/"):
        with Image.open(path) as image:
            width, height = image.size
            image.verify()
        text = f"Demo 图片理解：{width}×{height} 像素的活动图片。未识别或推断人物身份，请人工补充场景说明。"
        return ParseResult(text=text, summary=text, category="PHOTO", status="NEEDS_REVIEW", is_demo=True)
    raise ValueError(f"Unsupported parser: {suffix}")
