import re
from pathlib import Path

from sqlalchemy.orm import Session

from workbench.exports.markdown import write_markdown_export


def markdown_to_plain_text(markdown: str) -> str:
    text = re.sub(r"<!--.*?-->", "", markdown, flags=re.S)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"[*_`>]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def write_plain_text_export(session: Session, draft_id: str, exports_root: Path, confirm_high: bool = False, include_notes: bool = False) -> Path:
    markdown_path = write_markdown_export(session, draft_id, exports_root, confirm_high, include_notes)
    text = markdown_to_plain_text(markdown_path.read_text(encoding="utf-8")) + "\n"
    target = markdown_path.with_suffix(".txt")
    target.write_text(text, encoding="utf-8")
    markdown_path.unlink()
    return target
