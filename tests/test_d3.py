from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.seed import seed_database
from backend.services.report_service import build_decision_report


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "d3.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
    _sessions.clear()


def login(client: TestClient, username: str = "worker") -> dict:
    response = client.post("/api/auth/login", json={"username": username, "password": username + "1234"})
    assert response.status_code == 200
    return response.json()


def by_name(report: dict, name: str) -> dict:
    return next(row for row in report["products"] if row["product_name"] == name)


def stock(client: TestClient, code: str) -> dict:
    return next(row for row in client.get("/api/stock-options/balances?positive_only=false").json()
                if row["location_code"] == code)


def submit_adjustment(client: TestClient, row: dict, *, kind: str, qty: int) -> int:
    payload = {"lot_id": row["lot_id"], "location_id": row["location_id"],
               "kind": kind, "reason": "測試盤點" if kind == "COUNT" else "測試壓損"}
    payload["observed_qty" if kind == "COUNT" else "damaged_qty"] = qty
    result = client.post("/api/adjustments", json=payload)
    assert result.status_code == 201
    return result.json()["id"]


def approve(client: TestClient, request_id: int):
    result = client.post(f"/api/adjustments/{request_id}/review", json={"action": "APPROVE"})
    assert result.status_code == 200
    return result.json()


def test_admin_only_seed_and_active_products_without_lots_are_zero(client: TestClient):
    assert client.get("/api/reports").status_code == 401
    login(client)
    assert client.get("/api/reports").status_code == 403
    with database.connect_database() as connection:
        connection.execute("INSERT INTO products (name, unit, min_qty, target_qty) VALUES ('空箱品項', '箱', 2, 5)")
        connection.execute("INSERT INTO products (name, unit, min_qty, target_qty) VALUES ('零門檻品項', '公斤', 0, 0)")
        connection.execute("INSERT INTO products (name, unit, min_qty, target_qty, is_active) VALUES ('停用品項', '盒', 1, 2, 0)")
        connection.commit()
    login(client, "admin")
    response = client.get("/api/reports")
    assert response.status_code == 200
    report = response.json()
    assert report["as_of_utc"].endswith("Z")
    assert report["summary"] == {
        "active_product_count": 4, "in_stock_product_count": 2,
        "low_stock_product_count": 1, "pending_adjustment_count": 0,
        "shortage_demand_count": 0,
    }
    empty = by_name(report, "空箱品項")
    assert (empty["current_qty"], empty["is_low"], empty["replenishment_gap"], empty["unit"]) == (0, True, 5, "箱")
    assert empty["outbound_30d"] == 0
    zero_threshold = by_name(report, "零門檻品項")
    assert zero_threshold["current_qty"] == 0 and zero_threshold["is_low"] is False
    assert "停用品項" not in {row["product_name"] for row in report["products"]}
    assert by_name(report, "紅蘿蔔")["current_qty"] == 5
    assert by_name(report, "青花菜")["current_qty"] == 3
    assert len(report["aged_lots"]) == 2
    assert report["adjustments"] == []


def test_recent_outbound_uses_one_utc_window_and_refreshes_from_database(client: TestClient):
    login(client)
    carrot = stock(client, "B-03")
    result = client.post("/api/outbound", json={
        "lot_id": carrot["lot_id"], "location_id": carrot["location_id"], "qty": 2,
    })
    assert result.status_code == 201
    login(client, "admin")
    current = client.get("/api/reports").json()
    assert by_name(current, "紅蘿蔔")["current_qty"] == 3
    assert by_name(current, "紅蘿蔔")["outbound_30d"] == 2
    fixed_now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    cutoff = fixed_now - timedelta(days=30)
    with database.connect_database() as connection:
        worker_id = connection.execute("SELECT id FROM users WHERE username='worker'").fetchone()[0]
        connection.execute("UPDATE stock_movements SET created_at = ? WHERE id = ?",
                           ((cutoff - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                            result.json()["movement_id"]))
        for qty, stamp in [(3, cutoff), (7, cutoff - timedelta(seconds=1)),
                           (9, fixed_now + timedelta(seconds=1))]:
            connection.execute("""INSERT INTO stock_movements
                (kind, lot_id, from_location_id, qty, actor_id, created_at)
                VALUES ('OUTBOUND', ?, ?, ?, ?, ?)""",
                (carrot["lot_id"], carrot["location_id"], qty, worker_id,
                 stamp.strftime("%Y-%m-%d %H:%M:%S")))
        connection.commit()
    report = build_decision_report(fixed_now).model_dump()
    assert by_name(report, "紅蘿蔔")["outbound_30d"] == 3
    assert by_name(report, "青花菜")["outbound_30d"] == 0
    assert by_name(report, "紅蘿蔔")["current_qty"] == 3


def test_age_by_lot_and_zero_balance_excluded_from_age_list(client: TestClient):
    fixed_now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
    with database.connect_database() as connection:
        carrot_id = connection.execute("SELECT id FROM products WHERE name='紅蘿蔔'").fetchone()[0]
        worker_id = connection.execute("SELECT id FROM users WHERE username='worker'").fetchone()[0]
        location_id = connection.execute("SELECT id FROM locations WHERE code='A-01'").fetchone()[0]
        cursor = connection.execute("""INSERT INTO lots
            (lot_code, product_id, received_date, created_by)
            VALUES ('OLD-CARROT', ?, '2026-01-01', ?)""", (carrot_id, worker_id))
        connection.execute("INSERT INTO stock_balances VALUES (?, ?, 2)", (cursor.lastrowid, location_id))
        connection.commit()
    report = build_decision_report(fixed_now).model_dump()
    assert by_name(report, "紅蘿蔔")["current_qty"] == 7
    assert report["aged_lots"][0]["lot_code"] == "OLD-CARROT"
    assert report["aged_lots"][0]["age_days"] == (date(2026, 9, 26) - date(2026, 1, 1)).days
    assert report["aged_lots"][0]["total_qty"] == 2
    assert next(row for row in report["aged_lots"] if row["lot_code"] == "LOT-20260924-901")["age_days"] == 2
    with database.connect_database() as connection:
        connection.execute("UPDATE stock_balances SET qty=0 WHERE lot_id=(SELECT id FROM lots WHERE lot_code='OLD-CARROT')")
        connection.commit()
    refreshed = build_decision_report(fixed_now).model_dump()
    assert "OLD-CARROT" not in {row["lot_code"] for row in refreshed["aged_lots"]}


def test_pending_then_approved_count_and_scrap_are_separate(client: TestClient):
    login(client)
    carrot = stock(client, "B-03")
    broccoli = stock(client, "B-04")
    count_id = submit_adjustment(client, carrot, kind="COUNT", qty=0)
    scrap_id = submit_adjustment(client, broccoli, kind="SCRAP", qty=1)
    login(client, "admin")
    pending = client.get("/api/reports").json()
    assert pending["summary"]["pending_adjustment_count"] == 2
    assert by_name(pending, "紅蘿蔔")["count_loss_qty"] == 0
    assert by_name(pending, "青花菜")["scrap_qty"] == 0
    approve(client, count_id)
    approve(client, scrap_id)
    report = client.get("/api/reports").json()
    assert report["summary"]["pending_adjustment_count"] == 0
    assert report["summary"]["in_stock_product_count"] == 1
    assert report["summary"]["low_stock_product_count"] == 1
    assert (by_name(report, "紅蘿蔔")["current_qty"], by_name(report, "紅蘿蔔")["count_loss_qty"], by_name(report, "紅蘿蔔")["scrap_qty"]) == (0, 5, 0)
    assert (by_name(report, "青花菜")["current_qty"], by_name(report, "青花菜")["count_loss_qty"], by_name(report, "青花菜")["scrap_qty"]) == (2, 0, 1)
    assert {row["kind"] for row in report["adjustments"]} == {"COUNT_LOSS", "SCRAP"}
    assert {row["adjustment_request_id"] for row in report["adjustments"]} == {count_id, scrap_id}
    assert all(row["created_at"].endswith("Z") for row in report["adjustments"])
    assert "LOT-20260924-901" not in {row["lot_code"] for row in report["aged_lots"]}


def test_count_gain_zero_difference_and_rejected_request_not_added(client: TestClient):
    login(client)
    carrot = stock(client, "B-03")
    gain_id = submit_adjustment(client, carrot, kind="COUNT", qty=7)
    login(client, "admin")
    approve(client, gain_id)
    login(client)
    zero_id = submit_adjustment(client, carrot, kind="COUNT", qty=7)
    login(client, "admin")
    approve(client, zero_id)
    login(client)
    reject_id = submit_adjustment(client, carrot, kind="COUNT", qty=4)
    login(client, "admin")
    assert client.post(f"/api/adjustments/{reject_id}/review", json={"action": "REJECT", "review_note": "重查"}).status_code == 200
    report = client.get("/api/reports").json()
    product = by_name(report, "紅蘿蔔")
    assert product["current_qty"] == 7
    assert product["count_gain_qty"] == 2
    assert product["count_loss_qty"] == 0
    assert product["scrap_qty"] == 0
    assert [row["adjustment_request_id"] for row in report["adjustments"]] == [gain_id]
    assert report["summary"]["pending_adjustment_count"] == 0
