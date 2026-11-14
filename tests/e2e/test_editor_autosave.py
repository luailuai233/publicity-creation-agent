import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def test_editor_debounces_autosave_for_two_seconds_and_updates_status() -> None:
    script_path = Path(__file__).resolve().parents[2] / "workbench" / "static" / "js" / "editor.js"
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"),
            args=[f"--disk-cache-dir={os.environ['PLAYWRIGHT_BROWSER_CACHE']}"],
        )
        page = browser.new_page()
        page.route(
            "**/api/drafts/draft-1",
            lambda route, request: (
                requests.append(request.post_data_json),
                route.fulfill(status=200, content_type="application/json", body='{"data":{"updated_at":"12:34:56","word_count":8,"citation_count":2},"error":null,"requestId":"r1"}'),
            )[-1],
        )
        page.set_content(
            '<base href="http://workbench.test/">'
            '<textarea data-editor data-draft-id="draft-1">初稿</textarea>'
            '<span data-word-count>2</span><span data-citation-count>2</span><span data-save-time>未保存</span>'
        )
        page.add_script_tag(path=str(script_path))

        page.locator("[data-editor]").fill("这是人工修改后的正文")
        page.wait_for_timeout(1200)
        assert requests == []
        page.wait_for_timeout(1000)
        assert requests == [{"content": "这是人工修改后的正文"}]
        assert page.locator("[data-word-count]").inner_text() == "8"
        assert page.locator("[data-citation-count]").inner_text() == "2"
        assert page.locator("[data-save-time]").inner_text() == "12:34:56"
        browser.close()
