import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def test_home_cta_and_inspiration_grid_are_responsive(demo_client) -> None:
    client, _ = demo_client
    client.post("/api/demo/reset")
    home = client.get("/").text
    css = (Path(__file__).resolve().parents[2] / "workbench" / "static" / "css" / "app.css").read_text(encoding="utf-8")
    inspiration_css = (Path(__file__).resolve().parents[2] / "workbench" / "static" / "css" / "inspiration.css").read_text(encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH"), args=[f"--disk-cache-dir={os.environ['PLAYWRIGHT_BROWSER_CACHE']}"])
        for width, height in ((1440, 900), (1280, 800)):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_content(f"<style>{css}{inspiration_css}</style>{home}")
            assert page.locator("[data-demo-reset]").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
            page.set_content(f"<style>{css}{inspiration_css}</style><main class='inspiration-grid'><section>A</section><section>B</section><section>C</section></main>")
            assert page.locator(".inspiration-grid").evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length") == 3
            page.close()
        browser.close()

