from pathlib import Path

from workbench.db.base import Base
from workbench.db.models import AgentRun, FactCard, Material, Project, SourceChunk
from workbench.db.session import create_session_factory, create_sqlite_engine
from workbench.web.project_navigation import build_project_navigation


def build_session(tmp_path: Path):
    engine = create_sqlite_engine(tmp_path / "navigation.db")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)()


def test_navigation_has_seven_workspace_links_and_marks_current_page(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="导航项目")
    session.add(project); session.commit()

    navigation = build_project_navigation(session, project.id, f"/project/{project.id}/strategy")

    assert [item.href for item in navigation.items] == [
        "/",
        f"/project/{project.id}/materials",
        f"/project/{project.id}/facts",
        f"/project/{project.id}/inspiration",
        f"/project/{project.id}/strategy",
        f"/project/{project.id}/editor",
        f"/project/{project.id}/export",
    ]
    assert [item.label for item in navigation.items] == ["我的桌面", "活动文件", "事实确认", "灵感收藏", "编辑提案", "推文日志", "发布检查"]
    assert [item.label for item in navigation.items if item.is_active] == ["编辑提案"]
    assert navigation.items[2].prerequisite == "请先上传并解析活动素材"
    assert navigation.items[3].prerequisite == "请先确认可用活动事实"
    assert navigation.manual_writes_locked is False


def test_navigation_derives_progress_and_locks_only_active_agent_runs(tmp_path: Path) -> None:
    session = build_session(tmp_path)
    project = Project(name="状态项目")
    session.add(project); session.flush()
    material = Material(project_id=project.id, file_name="note.txt", mime_type="text/plain", parse_status="DONE")
    session.add(material); session.flush()
    session.add(SourceChunk(material_id=material.id, content="活动在礼堂举行"))
    session.add(FactCard(project_id=project.id, type="EVENT", content="活动举行", status="PENDING", confidence=0.9))
    session.add(AgentRun(project_id=project.id, goal="生成稿件", status="RUNNING", active_key=project.id))
    session.commit()

    active = build_project_navigation(session, project.id, f"/project/{project.id}/materials")
    assert active.items[2].status == "待确认"
    assert active.manual_writes_locked is True
    assert active.lock_message == "Agent 正在运行，结果页面可查看；暂停或取消后可手动修改。"

    run = session.query(AgentRun).filter_by(project_id=project.id).one()
    run.status = "PAUSED"
    run.active_key = None
    session.commit()
    paused = build_project_navigation(session, project.id, f"/project/{project.id}/materials")
    assert paused.manual_writes_locked is False
