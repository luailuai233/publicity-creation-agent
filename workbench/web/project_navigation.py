from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from workbench.agent.snapshot import build_project_snapshot
from workbench.db.models import AgentRun


class ProjectNavigationItem(BaseModel):
    label: str
    href: str
    status: str
    is_active: bool = False
    prerequisite: str = ""
    icon: str = "□"


class ProjectNavigation(BaseModel):
    items: list[ProjectNavigationItem]
    manual_writes_locked: bool = False
    lock_message: str = ""
    run_status: Optional[str] = None


def build_project_navigation(session: Session, project_id: str, current_path: str) -> ProjectNavigation:
    snapshot = build_project_snapshot(session, project_id)
    run = session.scalar(
        select(AgentRun).where(AgentRun.project_id == project_id).order_by(AgentRun.updated_at.desc())
    )
    run_status = run.status if run else None
    locked = run_status in {"QUEUED", "RUNNING"}

    if snapshot.source_chunk_count == 0:
        materials_status = "未开始"
    else:
        materials_status = "已完成"
    if snapshot.fact_count == 0:
        facts_status = "未开始"
    elif snapshot.conflict_groups or snapshot.pending_fact_count:
        facts_status = "待确认"
    else:
        facts_status = "已完成"
    inspiration_status = "已完成" if snapshot.usable_reference_count else ("待分析" if snapshot.selected_reference_count else "未开始")
    strategy_status = "已完成" if snapshot.selected_strategy_id else ("待选择" if snapshot.strategy_count else "未开始")
    editor_status = "待更新" if snapshot.draft_is_stale else ("已完成" if snapshot.draft_id else "未开始")
    if snapshot.quality_status == "PASSED":
        quality_status = "已完成"
    elif snapshot.quality_status in {"BLOCKED", "FAILED", "STALE"} or snapshot.blocking_issue_count:
        quality_status = "待处理"
    else:
        quality_status = "未开始"

    definitions = [
        ("我的桌面", "/", "可用", "", "⌂"),
        ("活动文件", f"/project/{project_id}/materials", materials_status, "", "▤"),
        ("事实确认", f"/project/{project_id}/facts", facts_status, "请先上传并解析活动素材" if snapshot.source_chunk_count == 0 else "", "◆"),
        ("灵感收藏", f"/project/{project_id}/inspiration", inspiration_status, "请先确认可用活动事实" if snapshot.fact_count == 0 else "", "✦"),
        ("编辑提案", f"/project/{project_id}/strategy", strategy_status, "请先准备有效案例和方法卡" if snapshot.usable_reference_count == 0 else "", "▥"),
        ("推文日志", f"/project/{project_id}/editor", editor_status, "请先主动选择创作策略" if snapshot.selected_strategy_id is None else "", "✎"),
        ("发布检查", f"/project/{project_id}/export", quality_status, "请先生成正文" if snapshot.draft_id is None else "", "✓"),
    ]
    items = [
        ProjectNavigationItem(
            label=label,
            href=href,
            status=status,
            prerequisite=prerequisite,
            icon=icon,
            is_active=(current_path == "/" if href == "/" else current_path.rstrip("/") == href),
        )
        for label, href, status, prerequisite, icon in definitions
    ]
    return ProjectNavigation(
        items=items,
        manual_writes_locked=locked,
        lock_message="Agent 正在运行，结果页面可查看；暂停或取消后可手动修改。" if locked else "",
        run_status=run_status,
    )
