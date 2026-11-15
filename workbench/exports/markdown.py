from pathlib import Path
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, Project, QualityIssue


class ExportBlocked(RuntimeError):
    pass


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value).strip("-")
    return cleaned[:50] or "draft"


def write_markdown_export(session: Session, draft_id: str, exports_root: Path, confirm_high: bool = False) -> Path:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise LookupError(draft_id)
    if draft.status == "CHECK_INCOMPLETE":
        raise ExportBlocked("检查未完成，不能导出")
    if draft.status != "CHECKED":
        raise ExportBlocked("请先完成系统检查")
    factual_blocker = session.scalar(
        select(QualityIssue.id).where(
            QualityIssue.draft_id == draft_id,
            QualityIssue.type.in_(["MISSING_SOURCE", "FACT_CONFLICT"]),
            QualityIssue.status == "OPEN",
        ).limit(1)
    )
    if draft.quality_status == "BLOCKED" or factual_blocker:
        raise ExportBlocked("仍有未解决的事实来源或事实冲突，不能导出")
    high_open = session.scalar(
        select(QualityIssue.id).where(QualityIssue.draft_id == draft_id, QualityIssue.severity == "HIGH", QualityIssue.status == "OPEN").limit(1)
    )
    if high_open and not confirm_high:
        raise ExportBlocked("仍有未处理的高风险问题，需要显式确认")
    root = exports_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    project = session.get(Project, draft.project_id)
    target = (root / f"{_slug(project.name)}-{project.id[:8]}-v{draft.version}.md").resolve()
    if root not in target.parents:
        raise ExportBlocked("导出路径不安全")
    public_content = re.sub(r"<!--\s*block:[\w-]+\s*-->\s*", "", draft.content).strip()
    content = public_content + "\n\n---\n\n> 本文由本地 Demo 工作台整理，关键事实以已确认素材为准。\n"
    target.write_text(content, encoding="utf-8")
    return target
