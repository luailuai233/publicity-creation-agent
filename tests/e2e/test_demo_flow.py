import os

from playwright.sync_api import sync_playwright


def test_browser_runs_complete_demo_chain_and_exports_markdown(live_server) -> None:
    base_url, root = live_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"), args=[f"--disk-cache-dir={os.environ['PLAYWRIGHT_BROWSER_CACHE']}"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base_url)
        page.locator("[data-demo-reset] button").click()
        page.wait_for_url("**/materials")
        page.locator("[data-confirm-facts]").click()
        page.wait_for_url("**/inspiration")
        page.locator("[data-generate-strategies]").click()
        page.wait_for_url("**/strategy")
        page.locator("[data-select-strategy]").first.click()
        page.locator("[data-open-editor]").click()
        page.wait_for_url("**/editor")
        page.locator("[data-generate-draft]").click()
        page.wait_for_selector("[data-editor]")
        page.locator("[data-editor]").fill(page.locator("[data-editor]").input_value() + "\n\n人工复核完成。")
        page.wait_for_timeout(2200)
        page.locator("[data-enter-quality]").click()
        page.wait_for_url("**/export")
        page.locator("[data-run-check]").click()
        page.wait_for_selector("[data-export-draft]:not([disabled])")
        page.locator("[data-export-draft]").click()
        page.wait_for_function("document.querySelector('[data-export-path]').textContent.includes('已保存')")
        exports = list((root / "exports").glob("*.md"))
        assert len(exports) == 1
        assert "人工复核完成" in exports[0].read_text(encoding="utf-8")
        assert "<!-- block:" not in exports[0].read_text(encoding="utf-8")
        browser.close()
