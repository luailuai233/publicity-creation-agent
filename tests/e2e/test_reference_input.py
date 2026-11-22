import os

from playwright.sync_api import sync_playwright


def test_browser_adds_and_analyzes_pasted_reference(live_server) -> None:
    base_url, _ = live_server
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"),
            args=[f"--disk-cache-dir={os.environ['PLAYWRIGHT_BROWSER_CACHE']}"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        static_requests = []
        page.on("request", lambda request: static_requests.append(request.url))
        response = page.request.post(f"{base_url}/api/projects", data={"name": "真实案例录入"})
        project = response.json()["data"]

        page.goto(f"{base_url}/project/{project['id']}/inspiration")
        assert any("/static/js/app.js?v=" in url for url in static_requests)
        assert any("/static/css/inspiration.css?v=" in url for url in static_requests)
        form = page.locator("[data-reference-create]")
        form.locator('[name="source_label"]').fill("用户粘贴的公众号文章")
        form.locator('[name="input_type"]').select_option("TEXT")
        form.locator('[name="raw_text"]').fill("志愿者先整理物资，再邀请居民共同参与活动。")
        form.locator('button[type="submit"]').click()

        page.wait_for_selector(".reference-card:has-text('用户粘贴的公众号文章')")
        analyze = page.locator("[data-analyze-reference]").first
        analyze.click()
        page.wait_for_selector(".mechanism-card:has-text('通过具体行动形成温暖但不过度煽情的情绪递进')")
        page.wait_for_selector(".guidance-group:has-text('从具体细节进入主题')")
        assert "正在分析参考案例" not in page.locator("[data-workflow-status]").inner_text()
        browser.close()
