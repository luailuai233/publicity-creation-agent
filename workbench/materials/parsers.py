from dataclasses import dataclass
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from workbench.materials.image_understanding import understand_image


@dataclass(frozen=True)
class ParsedChunk:
    content: str
    page: int | None = None
    paragraph: int | None = None
    location: str = ""


@dataclass(frozen=True)
class ParseResult:
    text: str
    summary: str
    category: str
    status: str = "DONE"
    is_demo: bool = False
    chunks: tuple[ParsedChunk, ...] = ()


def _summary(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:180] + ("…" if len(compact) > 180 else "")


def parse_path(path: Path, mime_type: str, *, image_provider=None, image_description: str | None = None) -> ParseResult:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        return ParseResult(text=text, summary=_summary(text), category="NOTE", chunks=(ParsedChunk(text, paragraph=1, location="paragraph:1"),))
    if suffix == ".docx":
        document = Document(path)
        chunks = [
            ParsedChunk(paragraph.text.strip(), paragraph=index, location=f"paragraph:{index}")
            for index, paragraph in enumerate(document.paragraphs, start=1)
            if paragraph.text.strip()
        ]
        for table_index, table in enumerate(document.tables, start=1):
            for row_index, row in enumerate(table.rows, start=1):
                content = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if content:
                    chunks.append(ParsedChunk(content, location=f"table:{table_index}:row:{row_index}"))
        text = "\n".join(chunk.content for chunk in chunks)
        return ParseResult(text=text, summary=_summary(text), category="OTHER", chunks=tuple(chunks))
    if suffix == ".pdf":
        chunks = []
        for page_number, page in enumerate(PdfReader(str(path)).pages, start=1):
            for block_number, block in enumerate((page.extract_text() or "").split("\n\n"), start=1):
                if block.strip():
                    chunks.append(ParsedChunk(block.strip(), page=page_number, location=f"page:{page_number}:block:{block_number}"))
        text = "\n".join(chunk.content for chunk in chunks)
        return ParseResult(text=text, summary=_summary(text), category="OTHER", status="DONE" if chunks else "NEEDS_REVIEW", chunks=tuple(chunks))
    if mime_type.startswith("image/"):
        image_result = understand_image(path, provider=image_provider, human_description=image_description)
        return ParseResult(
            text=image_result.text,
            summary=image_result.summary,
            category="PHOTO",
            status=image_result.status,
            is_demo=False,
            chunks=(ParsedChunk(image_result.text, paragraph=1, location="image:description"),) if image_result.text else (),
        )
    raise ValueError(f"Unsupported parser: {suffix}")
