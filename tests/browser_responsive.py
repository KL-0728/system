"""Visual-layout smoke test: build frontend, then python -m tests.browser_responsive."""
from pathlib import Path
import re
import sys
import tempfile
import threading
import time

from playwright.sync_api import expect, sync_playwright
import uvicorn

import backend.database as database
from backend.seed import seed_database

WIDTHS = (320, 390, 768, 851, 900, 1024, 1280)


def check_width(page, name, width):
    page.wait_for_load_state("networkidle")
    dimensions = page.evaluate("""() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    })""")
    assert dimensions["document"] <= dimensions["viewport"], f"{name} at {width}px: {dimensions}"
    assert dimensions["body"] <= dimensions["viewport"], f"{name} at {width}px: {dimensions}"
    if name == "worker 倉管操作":
        date_inside_card = page.evaluate("""() => {
          const card = document.querySelector('.inbound-panel').getBoundingClientRect();
          const frame = document.querySelector('.inbound-panel .date-input-frame').getBoundingClientRect();
          const input = document.querySelector('.inbound-panel input[type=date]');
          const padding = getComputedStyle(input);
          const field = input.getBoundingClientRect();
          return frame.left >= card.left && frame.right <= card.right
            && field.left >= frame.left && field.right <= frame.right
            && padding.paddingLeft === '0px' && padding.paddingRight === '0px';
        }""")
        assert date_inside_card, f"inbound date overflows its card at {width}px"
    if width <= 390:
        undersized = page.evaluate("""() => [...document.querySelectorAll('button,input,select,textarea')]
          .filter(el => el.offsetParent !== null && el.type !== 'checkbox')
          .map(el => ({ text: el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 25), height: el.getBoundingClientRect().height }))
          .filter(el => el.height < 44)""")
        assert undersized == [], f"{name} at {width}px has small controls: {undersized}"


def run(screenshots=False):
    review_dir = Path("data/ui-review") if screenshots else None
    if review_dir:
        review_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="inventory-responsive-") as directory:
        database.DATABASE_PATH = Path(directory) / "inventory.db"
        database.initialize_database()
        seed_database(database.DATABASE_PATH)
        from backend.main import app

        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18766, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(.1)
            assert server.started, "test server did not start"
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
                try:
                    for role in ("worker", "admin"):
                        context = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark")
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto("http://127.0.0.1:18766")
                        expect(page.locator(".theme-control button")).to_have_count(1)
                        expect(page.locator(".theme-switch")).to_have_attribute("aria-label", re.compile("跟隨系統"))
                        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                        expect(page.locator(".theme-switch svg circle")).to_have_count(1)
                        page.emulate_media(color_scheme="light")
                        expect(page.locator("html")).to_have_attribute("data-theme", "light")
                        page.emulate_media(color_scheme="dark")
                        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                        for width in WIDTHS:
                            page.set_viewport_size({"width": width, "height": 844})
                            check_width(page, f"{role} login", width)
                            if review_dir and width == 390 and role == "worker":
                                page.screenshot(path=str(review_dir / "login-mobile.png"))
                        page.locator(".theme-switch").click()
                        expect(page.locator("html")).to_have_attribute("data-theme", "light")
                        expect(page.locator(".theme-switch svg circle")).to_have_count(0)
                        page.reload()
                        expect(page.locator(".theme-switch")).to_have_attribute("aria-label", re.compile("^淺色"))
                        expect(page.locator("html")).to_have_attribute("data-theme", "light")
                        page.emulate_media(color_scheme="light")
                        expect(page.locator("html")).to_have_attribute("data-theme", "light")
                        page.emulate_media(color_scheme="dark")
                        expect(page.locator("html")).to_have_attribute("data-theme", "light")
                        page.locator(".theme-switch").click()
                        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                        page.get_by_label("帳號").fill(role)
                        page.get_by_label("密碼").fill(f"{role}1234")
                        page.get_by_role("button", name="登入", exact=True).click()
                        expect(page.get_by_role("button", name="登出")).to_be_visible()
                        destinations = ["首頁", "倉管操作"]
                        if role == "admin":
                            destinations += ["審核申請", "決策報表", "基本資料"]
                        for name in destinations:
                            page.get_by_role("button", name=name, exact=True).click()
                            for width in WIDTHS:
                                page.set_viewport_size({"width": width, "height": 844})
                                check_width(page, f"{role} {name}", width)
                                assert page.get_by_role("button", name=name, exact=True).is_visible()
                                if review_dir and ((role, name, width) in {
                                    ("worker", "倉管操作", 390),
                                    ("admin", "首頁", 1280),
                                    ("admin", "基本資料", 320),
                                    ("admin", "基本資料", 390),
                                    ("admin", "決策報表", 390),
                                }):
                                    page.screenshot(path=str(review_dir / f"{role}-{name}-{width}.png"))
                                if review_dir and role == "worker" and name == "倉管操作" and width in (320, 390):
                                    page.locator(".inbound-panel input[type=date]").scroll_into_view_if_needed()
                                    page.screenshot(path=str(review_dir / f"inbound-date-{width}.png"))
                        page.reload()
                        expect(page.locator(".theme-switch")).to_be_visible()
                        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                        assert errors == [], errors
                        context.close()
                    print("PASS: login, both roles' pages, 320/390/768/851/900/1024/1280px, 44px controls, theme system/manual/persistence, no JS errors")
                    if review_dir:
                        print(f"Screenshots: {review_dir}")
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "test server did not stop"


if __name__ == "__main__":
    run("--screenshots" in sys.argv)
