from pathlib import Path
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.db.models import Draft, DraftCitation, FactCard, Project, QualityIssue, Strategy


class ExportBlocked(RuntimeError):
    pass


def export_block_reason(draft: Draft | None, issues: list[QualityIssue]) -> str | None:
    """Return the user-facing reason that export is unavailable, if any."""
    if draft is None:
        return "请先生成正文"
    if draft.status == "CHECK_INCOMPLETE":
        return "检查未完成，不能导出"
    if draft.status != "CHECKED":
        return "请先完成系统检查"
    if draft.quality_status == "BLOCKED" or any(
        issue.resolution_policy == "HARD" and issue.status == "OPEN" for issue in issues
    ):
        return "仍有未解决的硬风险，不能导出"
    if any(
        issue.resolution_policy == "SOFT"
        and (issue.status == "OPEN" or (issue.status == "ACCEPTED" and not issue.resolution_note.strip()))
        for issue in issues
    ):
        return "仍有未处理或未记录确认说明的软风险，不能导出"
    return None


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value).strip("-")
    return cleaned[:50] or "draft"


def build_markdown_export(session: Session, draft: Draft, include_notes: bool = True) -> str:
    public_content = re.sub(r"<!--\s*block:[\w-]+\s*-->\s*", "", draft.content).strip()
    if not include_notes:
        return public_content + "\n"
    strategy = session.get(Strategy, draft.strategy_id)
    fact_ids = list(session.scalars(select(FactCard.content).join(DraftCitation, FactCard.id == DraftCitation.fact_id).where(DraftCitation.draft_id == draft.id)).all())
    issues = list(session.scalars(select(QualityIssue).where(QualityIssue.draft_id == draft.id, QualityIssue.status == "OPEN")).all())
    methods = strategy.method_summary if strategy and strategy.method_summary else "未采用外部案例方法"
    fact_summary = "、".join(dict.fromkeys(fact_ids)) or "无额外事实引用"
    pending = "\n".join(f"- {issue.message}" for issue in issues) or "- 无"
    return f"{public_content}\n\n## 创作说明\n\n- 已用事实：{fact_summary}\n- 创作方法：{methods}\n\n## 待确认清单\n\n{pending}\n"


def write_markdown_export(session: Session, draft_id: str, exports_root: Path, confirm_high: bool = False, include_notes: bool = True) -> Path:
    draft = session.get(Draft, draft_id)
    if draft is None:
        raise LookupError(draft_id)
    issues = list(session.scalars(select(QualityIssue).where(QualityIssue.draft_id == draft_id)).all())
    block_reason = export_block_reason(draft, issues)
    if block_reason:
        raise ExportBlocked(block_reason)
    root = exports_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    project = session.get(Project, draft.project_id)
    target = (root / f"{_slug(project.name)}-{project.id[:8]}-v{draft.version}.md").resolve()
    if root not in target.parents:
        raise ExportBlocked("导出路径不安全")
    content = build_markdown_export(session, draft, include_notes)
    target.write_text(content, encoding="utf-8")
    return target
