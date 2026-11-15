from pathlib import Path

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.db.projects import create_project
from workbench.db.models import AgentRun
from workbench.domain.project_schemas import ProjectCreate
from workbench.main import create_app
from workbench.settings import Settings


def build_project_client(tmp_path: Path):
    app = create_app(Settings(project_root=tmp_path, mock_ai_delay_ms=0))
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        project = create_project(session, ProjectCreate(name="Agent 工作台"))
    return app, TestClient(app), project


def test_agent_workspace_renders_goal_settings_stages_and_single_primary_action(tmp_path: Path) -> None:
    _app, client, project = build_project_client(tmp_path)
    with client:
        response = client.get(f"/project/{project.id}/agent")

    assert response.status_code == 200
    assert "创作目标" in response.text
    assert "校园活动关注者" in response.text
    assert "真实、温暖、克制" in response.text
    assert "1200–1600" in response.text
    assert response.text.count('class="primary-action') == 1
    assert "开始自主创作" in response.text
    for stage in ("资料解析", "事实校验", "案例分析", "策略规划", "内容生成", "质量检查"):
        assert stage in response.text
    assert "Demo 模拟结果" in response.text
    assert "当前计划" in response.text
    assert "chain-of-thought" not in response.text.lower()


def test_product_pages_are_workspaces_not_manual_generation_chain(tmp_path: Path) -> None:
    _app, client, project = build_project_client(tmp_path)
    with client:
        inspiration = client.get(f"/project/{project.id}/inspiration").text
        strategy = client.get(f"/project/{project.id}/strategy").text
        editor = client.get(f"/project/{project.id}/editor").text
        quality = client.get(f"/project/{project.id}/export").text

    assert "分析案例并生成 3 个策略" not in inspiration
    assert "Agent 会自动分析" in inspiration
    assert "Agent 推荐" in strategy
    assert "生成标题与大纲" not in strategy
    assert "标题与大纲尚未生成" not in editor
    assert "最终审核" in quality
    assert "最多自动修订 1 次" in quality


def test_completed_workspace_links_to_results(tmp_path: Path) -> None:
    app, client, project = build_project_client(tmp_path)
    with app.state.session_factory() as session:
        session.add(AgentRun(project_id=project.id, goal="完成", status="COMPLETED"))
        session.commit()
    with client:
        text = client.get(f"/project/{project.id}/agent").text
    assert f'/project/{project.id}/strategy' in text
    assert f'/project/{project.id}/editor' in text
    assert f'/project/{project.id}/export' in text
    assert "审核最终稿" in text
