import os

from playwright.sync_api import sync_playwright


def test_browser_material_upload_stays_in_workbench_and_shows_file(live_server, tmp_path) -> None:
    base_url, _ = live_server
    upload = tmp_path / "activity.txt"
    upload.write_text("11 月 22 日举行支教团迎新活动。", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"),
            args=[f"--disk-cache-dir={os.environ['PLAYWRIGHT_BROWSER_CACHE']}"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        project = page.request.post(f"{base_url}/api/projects", data={"name": "素材上传回归"}).json()["data"]
        materials_url = f"{base_url}/project/{project['id']}/materials"

        page.goto(materials_url)
        page.locator('.upload-box input[type="file"]').set_input_files(upload)
        page.locator('.upload-box button[type="submit"]').click()

        page.wait_for_url(materials_url)
        page.wait_for_selector(".material-row:has-text('activity.txt')")
        assert page.locator("body").get_attribute("class") != "json-formatter-container"
        browser.close()
