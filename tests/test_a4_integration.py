"""A4 展示流程：兩個獨立登入裝置共用同一個暫存資料庫。"""

from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.schemas.inbound import taiwan_today
from backend.seed import seed_database


@pytest.fixture()
def devices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "a4.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as desktop, TestClient(app) as phone:
        yield desktop, phone
    _sessions.clear()


def login(client: TestClient, username: str):
    response = client.post("/api/auth/login", json={
        "username": username, "password": username + "1234",
    })
    assert response.status_code == 200


def product(report: dict, name: str) -> dict:
    return next(row for row in report["products"] if row["product_name"] == name)


def positions(client: TestClient, lot_id: int) -> dict[str, int]:
    response = client.get("/api/inventory/stock")
    assert response.status_code == 200
    return {row["location_code"]: row["qty"] for row in response.json() if row["lot_id"] == lot_id}


def test_full_showcase_across_two_logged_in_devices(devices):
    desktop, phone = devices
    assert desktop.get("/api/reports").status_code == 401
    login(desktop, "admin")
    login(phone, "worker")
    assert phone.get("/api/reports").status_code == 403

    locations = {row["code"]: row["id"] for row in phone.get("/api/master-data/locations").json()}
    created = desktop.post("/api/master-data/products", json={
        "name": "甘藍菜", "unit": "籠", "min_qty": 9, "target_qty": 15, "is_active": True,
    })
    assert created.status_code == 201, created.text
    cabbage_id = created.json()["id"]
    assert any(row["id"] == cabbage_id for row in phone.get("/api/master-data/products").json())

    receipt = phone.post("/api/inventory/inbound", json={
        "product_id": cabbage_id, "location_id": locations["A-01"],
        "qty": 10, "received_date": taiwan_today().isoformat(),
    })
    assert receipt.status_code == 201, receipt.text
    cabbage_lot = receipt.json()["lot_id"]
    assert positions(desktop, cabbage_lot) == {"A-01": 10}

    first_move = phone.post("/api/outbound/transfers", json={
        "lot_id": cabbage_lot, "from_location_id": locations["A-01"],
        "to_location_id": locations["B-02"], "qty": 4,
    })
    assert first_move.status_code == 201, first_move.text
    assert positions(desktop, cabbage_lot) == {"A-01": 6, "B-02": 4}

    outbound = phone.post("/api/outbound", json={
        "lot_id": cabbage_lot, "location_id": locations["A-01"], "qty": 2,
    })
    assert outbound.status_code == 201, outbound.text
    report = desktop.get("/api/reports").json()
    assert (product(report, "甘藍菜")["current_qty"], product(report, "甘藍菜")["replenishment_gap"],
            product(report, "甘藍菜")["outbound_30d"]) == (8, 7, 2)
    assert product(report, "甘藍菜")["is_low"] is True

    second_move = phone.post("/api/outbound/transfers", json={
        "lot_id": cabbage_lot, "from_location_id": locations["A-01"],
        "to_location_id": locations["A-02"], "qty": 2,
    })
    assert second_move.status_code == 201, second_move.text
    assert positions(desktop, cabbage_lot) == {"A-01": 2, "A-02": 2, "B-02": 4}
    history = desktop.get("/api/inventory/movements", params={"lot_id": cabbage_lot})
    assert history.status_code == 200
    assert {row["kind"] for row in history.json()} == {"RECEIPT", "TRANSFER", "OUTBOUND"}

    seed_lots = {row["lot_code"]: row["lot_id"] for row in phone.get("/api/stock-options/lots").json()}
    carrot_lot = seed_lots["LOT-20260924-901"]
    broccoli_lot = seed_lots["LOT-20260924-902"]
    count = phone.post("/api/adjustments", json={
        "lot_id": carrot_lot, "location_id": locations["B-03"],
        "kind": "COUNT", "observed_qty": 0, "reason": "現場盤點為零",
    })
    assert count.status_code == 201, count.text
    assert positions(desktop, carrot_lot) == {"B-03": 5}
    assert phone.post("/api/outbound", json={
        "lot_id": carrot_lot, "location_id": locations["B-03"], "qty": 1,
    }).status_code == 409
    assert any(row["id"] == count.json()["id"] for row in desktop.get("/api/adjustments/pending").json())
    approved_count = desktop.post(f"/api/adjustments/{count.json()['id']}/review", json={"action": "APPROVE"})
    assert approved_count.status_code == 200, approved_count.text
    assert positions(phone, carrot_lot) == {"B-03": 0}

    scrap = phone.post("/api/adjustments", json={
        "lot_id": broccoli_lot, "location_id": locations["B-04"],
        "kind": "SCRAP", "damaged_qty": 1, "reason": "壓壞一籠",
    })
    assert scrap.status_code == 201, scrap.text
    assert positions(desktop, broccoli_lot) == {"B-04": 3}
    approved_scrap = desktop.post(f"/api/adjustments/{scrap.json()['id']}/review", json={"action": "APPROVE"})
    assert approved_scrap.status_code == 200, approved_scrap.text
    assert positions(phone, broccoli_lot) == {"B-04": 2}

    report = desktop.get("/api/reports").json()
    assert (product(report, "紅蘿蔔")["current_qty"], product(report, "紅蘿蔔")["count_loss_qty"]) == (0, 5)
    assert (product(report, "青花菜")["current_qty"], product(report, "青花菜")["scrap_qty"]) == (2, 1)
    assert product(report, "甘藍菜")["current_qty"] == 8
    assert {row["kind"] for row in report["adjustments"]} == {"COUNT_LOSS", "SCRAP"}
    assert phone.post("/api/outbound", json={
        "lot_id": cabbage_lot, "location_id": locations["A-01"], "qty": 99,
    }).status_code == 409
    assert positions(desktop, cabbage_lot) == {"A-01": 2, "A-02": 2, "B-02": 4}
