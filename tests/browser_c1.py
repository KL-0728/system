"""Run after frontend build: python -m tests.browser_c1 (requires local Chrome)."""
from pathlib import Path
import tempfile
import threading
import time

import httpx
from playwright.sync_api import sync_playwright, expect
import uvicorn

import backend.database as database
from backend.seed import seed_database


def run():
    with tempfile.TemporaryDirectory(prefix="inventory-c1-") as directory:
        database.DATABASE_PATH = Path(directory) / "inventory.db"
        database.initialize_database()
        seed_database(database.DATABASE_PATH)
        from backend.main import app

        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18765, log_level="error"))
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
                    page = browser.new_page(viewport={"width": 390, "height": 844})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto("http://127.0.0.1:18765")
                    page.get_by_role("button", name="登入", exact=True).click()
                    page.get_by_role("button", name="倉管操作", exact=True).click()
                    selector = page.get_by_label("批次與儲位")
                    expect(selector).to_be_enabled()
                    with database.connect_database() as connection:
                        row = connection.execute("""SELECT b.lot_id, b.location_id FROM stock_balances b
                            JOIN locations l ON l.id=b.location_id WHERE l.code='B-03'""").fetchone()
                        lot_id, location_id = tuple(row)
                    selector.select_option(f"{lot_id}:{location_id}")
                    quantity = page.get_by_label("出庫數量")
                    submit = page.get_by_role("button", name="確認出庫", exact=True)
                    for invalid in ["0", "-1", "1.5", "99"]:
                        quantity.fill(invalid)
                        submit.click()
                        assert quantity.evaluate("el => !el.checkValidity()")
                    count = 0

                    def delayed(route):
                        nonlocal count
                        if route.request.method == "POST":
                            count += 1
                            expect(page.get_by_role("button", name="出庫處理中…")).to_be_disabled()
                            time.sleep(.3)
                        route.continue_()

                    page.route("**/api/outbound", delayed)
                    quantity.fill("2")
                    # Two submissions in one event loop also exercise the synchronous ref guard.
                    page.locator(".outbound-panel form").evaluate("form => { form.requestSubmit(); form.requestSubmit(); }")
                    expect(page.get_by_role("status")).to_contain_text("餘量 3 籠")
                    expect(page.locator(".outbound-records article")).to_have_count(1)
                    assert count == 1
                    page.unroute("**/api/outbound", delayed)
                    page.reload()
                    page.get_by_role("button", name="倉管操作", exact=True).click()
                    expect(selector).to_be_enabled()
                    selector.select_option(f"{lot_id}:{location_id}")
                    expect(page.locator(".outbound-panel .notice")).to_contain_text("目前餘量：3 籠")

                    def lose_response(route):
                        if route.request.method == "POST":
                            response = route.fetch()
                            assert response.status == 201
                            route.abort("failed")
                        else:
                            route.continue_()

                    page.route("**/api/outbound", lose_response)
                    quantity.fill("1")
                    submit.click()
                    expect(page.get_by_role("alert").first).to_contain_text("結果未確認")
                    expect(submit).to_be_disabled()
                    page.unroute("**/api/outbound", lose_response)
                    page.get_by_role("button", name="查詢紀錄／更新餘量").click()
                    expect(page.locator(".outbound-records article")).to_have_count(2)
                    expect(submit).to_be_disabled()
                    page.get_by_role("button", name="我已核對紀錄，開始新的操作").click()
                    expect(quantity).to_have_value("")
                    expect(page.locator(".outbound-panel .notice")).to_contain_text("目前餘量：2 籠")
                    with database.connect_database() as connection:
                        worker_id = connection.execute("SELECT id FROM users WHERE username='worker'").fetchone()[0]
                        connection.execute("""INSERT INTO adjustment_requests
                            (kind, lot_id, location_id, original_qty, observed_qty, reason, requested_by)
                            VALUES ('COUNT', ?, ?, 2, 1, '瀏覽器測試', ?)""", (lot_id, location_id, worker_id))
                        connection.commit()
                    page.get_by_role("button", name="查詢紀錄／更新餘量").click()
                    expect(page.locator(".outbound-panel .notice")).to_contain_text("待審凍結")
                    expect(submit).to_be_disabled()
                    for width in [320, 390, 1280]:
                        page.set_viewport_size({"width": width, "height": 844})
                        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"overflow at {width}px"
                    assert errors == [], errors
                    with httpx.Client(base_url="http://127.0.0.1:18765") as client:
                        client.post("/api/auth/login", json={"username": "worker", "password": "worker1234"})
                        assert len(client.get("/api/outbound").json()) == 2
                    print("PASS: real login, validation, double submit (one POST), persistence, lost response, pending freeze, 320/390/1280px, no JS errors")
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "test server did not stop"


if __name__ == "__main__":
    run()
