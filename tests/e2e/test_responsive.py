import os

from playwright.sync_api import sync_playwright


def test_actual_pages_keep_cta_visible_no_overflow_and_three_columns(live_server) -> None:
    base_url, _ = live_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"), args=[f"--disk-cache-dir={os.environ['PLAYWRIGHT_BROWSER_CACHE']}"])
        for width, height in ((1440, 900), (1280, 800)):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(base_url)
            assert page.locator("[data-demo-reset] button").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
            page.locator("[data-demo-reset] button").click(); page.wait_for_url("**/materials")
            project_id = page.url.split("/project/")[1].split("/")[0]
            page.goto(f"{base_url}/project/{project_id}/inspiration")
            assert page.locator("[data-generate-strategies]").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
            columns = page.locator(".inspiration-grid").evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length")
            assert columns == 3
            page.close()
        browser.close()
