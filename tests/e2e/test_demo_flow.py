import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def test_browser_runs_agent_chain_with_one_start_and_exports_markdown(live_server) -> None:
    base_url, root = live_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"), args=[f"--disk-cache-dir={os.environ['PLAYWRIGHT_BROWSER_CACHE']}"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base_url)
        page.locator("[data-demo-reset] button").click()
        page.wait_for_url("**/materials")
        project_id = page.url.split("/project/")[1].split("/")[0]
        page.locator("[data-confirm-facts]").click()
        page.wait_for_url("**/inspiration")
        page.locator("[data-analyze-reference]").first.click()
        page.wait_for_selector("[data-generate-strategies]")
        page.locator("[data-generate-strategies]").click()
        page.wait_for_url("**/strategy")
        assert page.locator(".proposal-window").count() == 3
        selected_button = page.locator("[data-select-strategy]").first
        selected_button.click()
        page.wait_for_selector("[data-select-strategy]:has-text('已选择')")
        page.goto(f"{base_url}/project/{project_id}/agent")
        page.locator("[data-agent-start] textarea").fill("生成一篇可溯源、真实温暖的活动长图文")
        page.locator("[data-agent-start] button[type=submit]").click()
        page.wait_for_selector("[data-agent-status]:has-text('COMPLETED')", timeout=15000)
        evidence_dir = Path(__file__).resolve().parents[2] / "test-results" / "acceptance"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=evidence_dir / "agent-completed.png", full_page=True)
        page.goto(f"{base_url}/project/{project_id}/export")
        page.wait_for_selector("[data-export-draft]:not([disabled])")
        page.screenshot(path=evidence_dir / "export-ready.png", full_page=True)
        page.locator("[data-export-draft]").click()
        page.wait_for_function("document.querySelector('[data-export-path]').textContent.includes('已保存')")
        exports = list((root / "exports").glob("*.md"))
        assert len(exports) == 1
        assert "这条信息来自已确认的活动素材" in exports[0].read_text(encoding="utf-8")
        assert "<!-- block:" not in exports[0].read_text(encoding="utf-8")
        browser.close()
