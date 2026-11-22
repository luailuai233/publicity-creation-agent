from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

from workbench.db.base import Base
from workbench.main import create_app
from workbench.settings import Settings


def test_inspiration_windows_render_saved_analysis_instead_of_placeholder_copy() -> None:
    template_root = Path(__file__).resolve().parents[3] / "workbench" / "templates"
    environment = Environment(loader=FileSystemLoader(template_root), autoescape=True)
    analysis = SimpleNamespace(
        hook="从课表上的手写改动切入",
        emotion="从备课压力递进到互相支持",
        structure="问题—协作—调整—回扣倾听",
        image_role="课表截图承担问题证据",
        transferable=["用改动痕迹建立悬念", "用协作行动承接价值"],
        avoid=["照搬原文标题", "虚构会议参与人数"],
    )

    mechanism_html = environment.get_template("inspiration/analysis_window.html").render(active_analysis=analysis)
    guidance_html = environment.get_template("inspiration/guidance_window.html").render(active_analysis=analysis)

    assert "从课表上的手写改动切入" in mechanism_html
    assert "从备课压力递进到互相支持" in mechanism_html
    assert "课表截图承担问题证据" in mechanism_html
    assert "用改动痕迹建立悬念" in guidance_html
    assert "虚构会议参与人数" in guidance_html


def test_strategy_generation_cta_shows_generate_or_agent_recovery_action() -> None:
    template_root = Path(__file__).resolve().parents[3] / "workbench" / "templates"
    environment = Environment(loader=FileSystemLoader(template_root), autoescape=True)
    template = environment.get_template("strategy/generate_cta.html")
    project = SimpleNamespace(id="project-1")

    ready = template.render(project=project, can_generate_strategies=True)
    blocked = template.render(project=project, can_generate_strategies=False)

    assert 'data-generate-strategies="project-1"' in ready
    assert "生成 3 个创作策略" in ready
    assert 'href="/project/project-1/agent"' in blocked
    assert "先让 Agent 整理活动事实" in blocked
    assert "data-generate-strategies" not in blocked


def test_inspiration_page_keeps_required_three_window_structure(tmp_path: Path) -> None:
    app = create_app(Settings(project_root=tmp_path))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "灵感布局"}).json()["data"]
        page = client.get(f"/project/{project['id']}/inspiration")
        css = client.get("/static/css/inspiration.css")

    assert page.status_code == 200
    assert page.text.count('class="reference-card') == 3
    assert page.text.count('class="mechanism-card') == 4
    assert page.text.count('class="guidance-group') == 3
    assert page.text.count('class="primary-action') == 0
    assert "Agent 会自动分析" in page.text
    assert 'class="inspiration-grid"' in page.text
    assert "grid-template-columns: minmax(0, 1.02fr) minmax(0, 1.07fr) minmax(0, .91fr)" in css.text
    assert "@media (max-width: 1280px)" in css.text
    assert "grid-template-columns" in css.text.split("@media (max-width: 1280px)", 1)[1]
    assert 'data-reference-create' in page.text
    assert 'name="input_type"' in page.text
    assert 'value="TEXT"' in page.text
    assert 'value="LINK"' in page.text
    assert 'value="SCREENSHOT"' in page.text
    assert 'name="raw_text"' in page.text
    assert 'name="source_url"' in page.text
    assert 'name="file"' in page.text
