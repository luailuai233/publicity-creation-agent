from pathlib import Path
import re

from fastapi.testclient import TestClient

from workbench.db.base import Base
from workbench.db.projects import create_project
from workbench.db.models import AgentRun, Draft, FactCard, FactSource, Material, QualityIssue, SourceChunk, Strategy
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
    assert "Demo 模拟结果" not in response.text
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


def test_export_button_stays_disabled_until_every_issue_meets_its_resolution_policy(tmp_path: Path) -> None:
    app, client, project = build_project_client(tmp_path)
    with app.state.session_factory() as session:
        strategy = Strategy(
            project_id=project.id,
            name="测试策略",
            angle="测试角度",
            opening="测试开头",
            structure="测试结构",
            selected=True,
        )
        session.add(strategy)
        session.flush()
        draft = Draft(
            project_id=project.id,
            strategy_id=strategy.id,
            title="测试稿件",
            content="正文",
            status="CHECKED",
            quality_status="NEEDS_CONFIRMATION",
        )
        session.add(draft)
        session.flush()
        session.add(
            QualityIssue(
                draft_id=draft.id,
                type="SIMILAR_EXPRESSION",
                severity="MEDIUM",
                message="表达相似",
                resolution_policy="SOFT",
                status="OPEN",
            )
        )
        session.commit()

    with client:
        response = client.get(f"/project/{project.id}/export")

    assert 'data-export-draft' in response.text
    assert 'data-export-draft="' + draft.id + '" disabled' in response.text
    assert "请先处理全部风险项" in response.text


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


def test_strategy_selection_wait_links_to_proposals_without_generic_answer_form(tmp_path: Path) -> None:
    app, client, project = build_project_client(tmp_path)
    with app.state.session_factory() as session:
        session.add(
            AgentRun(
                project_id=project.id,
                goal="选择策略后继续",
                status="WAITING_USER",
                waiting_reason="STRATEGY_SELECTION",
            )
        )
        session.commit()

    with client:
        response = client.get(f"/project/{project.id}/agent")

    assert f'href="/project/{project.id}/strategy"' in response.text
    assert "前往编辑提案" in response.text
    assert "请选择一个创作策略后继续生成正文" in response.text
    assert "data-agent-answer" not in response.text


def seed_legacy_conflict_wait(app, project):
    with app.state.session_factory() as session:
        material = Material(project_id=project.id, file_name="活动流程.docx", mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        session.add(material)
        session.flush()
        first_chunk = SourceChunk(material_id=material.id, content="原文：活动共有 36 人参加。", paragraph=4)
        second_chunk = SourceChunk(material_id=material.id, content="原文：活动共有 12 人参加。", paragraph=7)
        session.add_all([first_chunk, second_chunk])
        session.flush()
        first = FactCard(project_id=project.id, type="NUMBER", content="36 人", status="CONFLICT", conflict_group="number-internal-id")
        second = FactCard(project_id=project.id, type="NUMBER", content="12 人", status="CONFLICT", conflict_group="number-internal-id")
        session.add_all([first, second])
        session.flush()
        session.add_all(
            [
                FactSource(fact_id=first.id, source_chunk_id=first_chunk.id),
                FactSource(fact_id=second.id, source_chunk_id=second_chunk.id),
            ]
        )
        run = AgentRun(
            project_id=project.id,
            goal="解决事实冲突",
            status="WAITING_USER",
            waiting_reason="FACT_CONFLICT",
            waiting_payload={
                "project_revision": project.revision,
                "questions": [
                    {
                        "id": "fact-conflict:number-internal-id",
                        "code": "FACT_CONFLICT",
                        "prompt": "请选择冲突组 number-internal-id 中的有效事实",
                        "reason": "关键事实存在冲突",
                        "affected_fact_ids": ["number-internal-id"],
                        "answer_type": "SINGLE_CHOICE",
                        "options": [],
                        "allow_free_text": False,
                    }
                ],
            },
        )
        session.add(run)
        session.commit()
        return first.id, second.id


def test_agent_waiting_form_expands_legacy_conflict_into_values_and_sources(tmp_path: Path) -> None:
    app, client, project = build_project_client(tmp_path)
    first_id, second_id = seed_legacy_conflict_wait(app, project)

    with client:
        response = client.get(f"/project/{project.id}/agent")

    assert response.status_code == 200
    assert "人数信息存在冲突，请选择正确的一项" in response.text
    assert "36 人" in response.text
    assert "12 人" in response.text
    assert "活动流程.docx · 第 4 段" in response.text
    assert "原文：活动共有 36 人参加。" in response.text
    assert f'value="{first_id}"' in response.text
    assert f'value="{second_id}"' in response.text


def test_fact_page_conflict_panel_shows_candidate_values_and_evidence(tmp_path: Path) -> None:
    app, client, project = build_project_client(tmp_path)
    seed_legacy_conflict_wait(app, project)

    with client:
        response = client.get(f"/project/{project.id}/facts")

    assert response.status_code == 200
    assert "36 人" in response.text
    assert "12 人" in response.text
    assert "活动流程.docx · 第 7 段" in response.text
    assert "原文：活动共有 12 人参加。" in response.text
    assert 'data-resolve-conflict="number-internal-id"' in response.text


def test_all_project_pages_render_visible_workflow_navigation_and_clean_product_copy(tmp_path: Path) -> None:
    _app, client, project = build_project_client(tmp_path)
    segments = ("agent", "materials", "facts", "inspiration", "strategy", "editor", "export")
    page_hrefs = [f'/project/{project.id}/{segment}' for segment in segments]
    expected_hrefs = ["/", *[href for segment, href in zip(segments, page_hrefs) if segment != "agent"]]
    with client:
        responses = {segment: client.get(href) for segment, href in zip(segments, page_hrefs)}

    for segment, response in responses.items():
        assert response.status_code == 200, segment
        assert 'aria-label="项目工作流"' in response.text
        for removed_copy in ("LOCAL · MOCK AI", "本地优先 · 自动保存", "Demo 模拟结果", "2 秒自动保存"):
            assert removed_copy not in response.text
        for href in expected_hrefs:
            workflow_link = rf'<a class="workflow-item[^\"]*"[^>]*href="{re.escape(href)}"[^>]*>'
            assert re.search(workflow_link, response.text), (segment, href)
        if segment != "agent":
            active_pattern = rf'class="workflow-item[^\"]*is-active[^\"]*"[^>]+href="/project/{project.id}/{segment}"'
            assert re.search(active_pattern, response.text), segment
