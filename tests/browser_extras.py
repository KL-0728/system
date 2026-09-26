"""Four optional features in a real browser, using only a temporary SQLite database."""
from datetime import timedelta
from pathlib import Path
import tempfile
import threading
import time

from playwright.sync_api import expect, sync_playwright
import uvicorn

import backend.database as database
from backend.schemas.inbound import taiwan_today
from backend.seed import seed_database


def login(page, username):
    page.goto("http://127.0.0.1:18767")
    page.get_by_label("帳號").fill(username)
    page.get_by_label("密碼").fill(username + "1234")
    page.get_by_role("button", name="登入", exact=True).click()
    expect(page.get_by_role("button", name="登出")).to_be_visible()
    page.get_by_role("button", name="倉管操作", exact=True).click()
    page.wait_for_load_state("networkidle")


def no_overflow(page, width):
    page.set_viewport_size({"width": width, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"overflow at {width}px"


def run():
    with tempfile.TemporaryDirectory(prefix="inventory-extras-browser-") as directory:
        database.DATABASE_PATH = Path(directory) / "inventory.db"
        database.initialize_database()
        seed_database(database.DATABASE_PATH)
        with database.connect_database() as connection:
            product_id = connection.execute(
                "INSERT INTO products (name, unit, min_qty, target_qty) VALUES ('零庫存示範', '箱', 1, 4)"
            ).lastrowid
            lot_id = connection.execute("SELECT id FROM lots WHERE lot_code = 'LOT-20260924-901'").fetchone()[0]
            source_id = connection.execute("SELECT id FROM locations WHERE code = 'B-03'").fetchone()[0]
            target_id = connection.execute("SELECT id FROM locations WHERE code = 'A-01'").fetchone()[0]
            connection.commit()
        from backend.main import app

        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18767, log_level="error"))
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
                    worker = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
                    page = worker.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    login(page, "worker")
                    shortage = page.locator(".shortage-panel")
                    shortage.get_by_label("品項").select_option(str(product_id))
                    shortage.get_by_label("詢問數量").fill("3")
                    shortage.get_by_role("button", name="記錄缺貨需求").click()
                    expect(shortage.get_by_role("status")).to_contain_text("不會扣除庫存")
                    expect(shortage.locator(".shortage-records article")).to_have_count(1)
                    page.reload()
                    page.get_by_role("button", name="倉管操作", exact=True).click()
                    expect(page.locator(".shortage-records article")).to_have_count(1)
                    location_map = page.locator(".location-map-panel")
                    location_map.get_by_role("button", name="B-03").click()
                    expect(location_map.locator(".location-map-detail")).to_contain_text("紅蘿蔔")
                    page.wait_for_function("""() => {
                      const detail = document.querySelector('.location-map-detail');
                      return detail && detail.getBoundingClientRect().top >= 0
                        && detail.getBoundingClientRect().top < window.innerHeight / 2;
                    }""")
                    transfer = page.locator(".transfer-panel")
                    transfer.get_by_label("移位來源（批次與儲位）").select_option(f"{lot_id}:{source_id}")
                    transfer.get_by_label("目標儲位").select_option(str(target_id))
                    transfer.get_by_label("移位數量").fill("1")
                    transfer.get_by_role("button", name="確認移位").click()
                    expect(transfer.get_by_role("status")).to_contain_text("移位 1 籠成功")
                    location_map.get_by_role("button", name="A-01").click()
                    expect(location_map.locator(".location-map-detail")).to_contain_text("紅蘿蔔")
                    expect(location_map.locator(".location-map-detail")).to_contain_text("1 籠")
                    for width in (320, 390, 768, 1280):
                        no_overflow(page, width)

                    with database.connect_database() as connection:
                        worker_id = connection.execute("SELECT id FROM users WHERE username='worker'").fetchone()[0]
                        second_lot = connection.execute("SELECT id FROM lots WHERE lot_code='LOT-20260924-902'").fetchone()[0]
                        second_location = connection.execute("SELECT id FROM locations WHERE code='B-04'").fetchone()[0]
                        for pending_lot, pending_location in ((lot_id, source_id), (second_lot, second_location)):
                            quantity = connection.execute(
                                "SELECT qty FROM stock_balances WHERE lot_id=? AND location_id=?",
                                (pending_lot, pending_location),
                            ).fetchone()[0]
                            connection.execute("""INSERT INTO adjustment_requests
                                (kind, lot_id, location_id, original_qty, observed_qty, reason, requested_by)
                                VALUES ('COUNT', ?, ?, ?, ?, '瀏覽器審核測試', ?)""",
                                (pending_lot, pending_location, quantity, quantity, worker_id))
                        connection.commit()

                    admin = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
                    admin_page = admin.new_page()
                    admin_page.on("pageerror", lambda error: errors.append(str(error)))
                    login(admin_page, "admin")
                    inventory = admin_page.locator(".inventory-panel")
                    lot = inventory.locator(".inventory-lot").filter(has_text="LOT-20260924-901")
                    lot.locator("summary").click()
                    lot.get_by_label("到期日").fill((taiwan_today() + timedelta(days=3)).isoformat())
                    lot.get_by_role("button", name="儲存效期").click()
                    expect(inventory.locator(".inventory-lot").filter(has_text="LOT-20260924-901")).to_contain_text("即將到期")
                    with admin_page.expect_download() as download_info:
                        inventory.get_by_role("button", name="匯出庫存 CSV").click()
                    download = download_info.value
                    assert download.suggested_filename.endswith(".csv")
                    assert "LOT-20260924-901" in Path(download.path()).read_text(encoding="utf-8-sig")
                    admin_page.get_by_role("button", name="決策報表", exact=True).click()
                    expect(admin_page.locator("#report-shortages")).to_contain_text("零庫存示範")
                    expect(admin_page.locator("#report-products")).to_contain_text("累計缺貨詢問 3 箱")
                    for width in (320, 390, 768, 1280):
                        no_overflow(admin_page, width)
                    admin_page.get_by_role("button", name="首頁", exact=True).click()
                    expect(admin_page.locator(".home-stats .report-summary")).to_be_visible()
                    gap = admin_page.evaluate("""() => {
                      const button = document.querySelector('.home-stats button');
                      const summary = document.querySelector('.home-stats .report-summary');
                      return summary.getBoundingClientRect().top - button.getBoundingClientRect().bottom;
                    }""")
                    assert gap >= 16, f"statistics button gap too small: {gap}"
                    admin_page.get_by_role("button", name="審核申請", exact=True).click()
                    pending = admin_page.locator("#review-pending .review-list article")
                    expect(pending).to_have_count(2)
                    pending.nth(0).get_by_role("button", name="查看詳情與審核").click()
                    expect(pending.nth(0).locator(".review-inline-detail")).to_be_visible()
                    assert pending.nth(1).locator(".review-inline-detail").count() == 0
                    pending.nth(1).get_by_role("button", name="查看詳情與審核").click()
                    expect(pending.nth(1).locator(".review-inline-detail")).to_be_visible()
                    assert pending.nth(0).locator(".review-inline-detail").count() == 0
                    for width in (320, 390, 768, 1280):
                        no_overflow(admin_page, width)
                    assert errors == [], errors
                    worker.close(); admin.close()
                    print("PASS: shortage persistence and report separation, map after transfer, expiry, CSV download, responsive layout")
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "test server did not stop"


if __name__ == "__main__":
    run()
