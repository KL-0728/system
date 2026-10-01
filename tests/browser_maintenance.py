"""Browser smoke test for the teacher's FIFO and warehouse count tasks."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import threading
import time

import httpx
from playwright.sync_api import expect, sync_playwright
import uvicorn

import backend.database as database
from backend.seed import seed_database


def run():
    with tempfile.TemporaryDirectory(prefix="inventory-maintenance-") as directory:
        database.DATABASE_PATH = Path(directory) / "inventory.db"
        database.initialize_database()
        seed_database(database.DATABASE_PATH)
        from backend.main import app

        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18768, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(.1)
            assert server.started
            with httpx.Client(base_url="http://127.0.0.1:18768") as client:
                assert client.post("/api/auth/login", json={"username": "worker", "password": "worker1234"}).status_code == 200
                product = next(row for row in client.get("/api/master-data/products").json() if row["name"] == "青花菜")
                location = next(row for row in client.get("/api/master-data/locations").json() if row["code"] == "B-02")
                now = datetime.now(timezone(timedelta(hours=8))).replace(second=0, microsecond=0)
                assert client.post("/api/inventory/inbound", json={
                    "product_id": product["id"], "location_id": location["id"], "qty": 2,
                    "received_date": now.date().isoformat(), "received_at": now.isoformat(timespec="minutes"),
                }).status_code == 201

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
                try:
                    page = browser.new_page(viewport={"width": 390, "height": 844})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto("http://127.0.0.1:18768")
                    page.get_by_label("帳號").fill("worker")
                    page.get_by_label("密碼").fill("worker1234")
                    page.get_by_role("button", name="登入", exact=True).click()
                    page.get_by_role("button", name="倉管操作", exact=True).click()
                    page.get_by_role("tab", name="出庫").click()
                    outbound = page.locator(".outbound-panel")
                    outbound.get_by_label("要出貨的品項").select_option(str(product["id"]))
                    expect(outbound.locator("div.notice")).to_contain_text("LOT-20260924-902")
                    expect(outbound.locator("div.notice")).to_contain_text("B-04")

                    count = page.locator(".count-panel")
                    page.get_by_role("tab", name="整庫盤點").click()
                    # The count page must still refresh after its module has been open longer than 10 seconds.
                    page.wait_for_timeout(10500)
                    count.get_by_role("button", name="重新讀取盤點進度").click()
                    expect(count.locator(".error")).to_have_count(0)
                    count.get_by_label("選擇倉庫").select_option(label="A 冷凍庫")
                    count.get_by_role("button", name="開始／接續盤點").click()
                    expect(count.locator(".count-item")).to_have_count(2)
                    count.get_by_role("button", name="一鍵確認所有未確認格").click()
                    expect(count.get_by_text("進度 2/2 格")).to_be_visible()
                    count.locator(".count-item").first.get_by_role("button", name="重新核對這一格").click()
                    expect(count.get_by_text("進度 1/2 格")).to_be_visible()
                    count.locator(".count-item").first.get_by_role("button", name="確認這一格").click()
                    expect(count.get_by_text("進度 2/2 格")).to_be_visible()
                    count.get_by_role("button", name="完成整庫盤點").click()
                    expect(count.get_by_text("整庫盤點已完成；目前沒有待審盤差，無須審核。", exact=True)).to_be_visible()
                    expect(count.get_by_role("heading", name="A 冷凍庫｜已完成")).to_be_visible()
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                    assert errors == [], errors
                    print("PASS: FIFO suggestion, warehouse checklist, completion, 390px viewport, no JS errors")
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=5)


if __name__ == "__main__":
    run()
