"""Teacher acceptance: receipt time, first-in-first-out hint data, full warehouse count."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.migrate_maintenance import backup_and_migrate, migrate_maintenance
from backend.seed import seed_database


@pytest.fixture()
def clients(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "maintenance.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as admin, TestClient(app) as worker:
        assert admin.post("/api/auth/login", json={"username": "admin", "password": "admin1234"}).status_code == 200
        assert worker.post("/api/auth/login", json={"username": "worker", "password": "worker1234"}).status_code == 200
        yield admin, worker
    _sessions.clear()


def test_receiving_time_and_fifo_order(clients):
    admin, worker = clients
    product = admin.post("/api/master-data/products", json={
        "name": "青江菜", "unit": "箱", "min_qty": 0, "target_qty": 0, "is_active": True,
    }).json()
    locations = {row["code"]: row["id"] for row in worker.get("/api/master-data/locations").json()}
    now = datetime.now(timezone(timedelta(hours=8))).replace(second=0, microsecond=0)
    for at, code in [(now - timedelta(days=2), "B-02"), (now - timedelta(days=1), "B-04")]:
        response = worker.post("/api/inventory/inbound", json={
            "product_id": product["id"], "location_id": locations[code], "qty": 2,
            "received_date": at.date().isoformat(), "received_at": at.isoformat(timespec="minutes"),
        })
        assert response.status_code == 201, response.text
    options = worker.get("/api/stock-options/balances").json()
    matching = [row for row in options if row["product_id"] == product["id"]]
    assert [row["location_code"] for row in matching] == ["B-02", "B-04"]
    assert all(row["received_at"] for row in matching)
    future = now + timedelta(days=1)
    rejected = worker.post("/api/inventory/inbound", json={
        "product_id": product["id"], "location_id": locations["B-02"], "qty": 1,
        "received_date": future.date().isoformat(), "received_at": future.isoformat(timespec="minutes"),
    })
    assert rejected.status_code == 422


def test_full_warehouse_count_and_separate_spoilage(clients):
    admin, worker = clients
    product = admin.post("/api/master-data/products", json={
        "name": "甘藍菜", "unit": "箱", "min_qty": 0, "target_qty": 0, "is_active": True,
    }).json()
    warehouse = next(row for row in worker.get("/api/master-data/warehouses").json() if row["code"] == "A")
    locations = {row["code"]: row["id"] for row in worker.get("/api/master-data/locations").json()}
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    receipt = worker.post("/api/inventory/inbound", json={
        "product_id": product["id"], "location_id": locations["A-01"], "qty": 2,
        "received_date": today,
    })
    assert receipt.status_code == 201
    started = worker.post("/api/warehouse-counts", json={"warehouse_id": warehouse["id"]})
    assert started.status_code == 201, started.text
    session = started.json()
    assert {row["location_code"] for row in session["items"]} == {"A-01", "A-02"}
    assert worker.post(f"/api/warehouse-counts/{session['id']}/complete").status_code == 409
    for item in session["items"]:
        response = worker.post(f"/api/warehouse-counts/{session['id']}/items/{item['id']}", json={
            "observed_qty": item["original_qty"], "note": "",
        })
        assert response.status_code == 200, (session, item, response.text)
    first = session["items"][0]
    reopened = worker.post(f"/api/warehouse-counts/{session['id']}/items/{first['id']}/reopen")
    assert reopened.status_code == 200, reopened.text
    assert next(row for row in reopened.json()["items"] if row["id"] == first["id"])["checked_at"] is None
    assert worker.post(f"/api/warehouse-counts/{session['id']}/complete").status_code == 409
    checked_again = worker.post(f"/api/warehouse-counts/{session['id']}/items/{first['id']}", json={
        "observed_qty": first["original_qty"], "note": "",
    })
    assert checked_again.status_code == 200, checked_again.text
    completed = worker.post(f"/api/warehouse-counts/{session['id']}/complete")
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETE"
    assert admin.get("/api/adjustments/pending").json() == []
    scrap = worker.post("/api/adjustments", json={
        "kind": "SCRAP", "lot_id": receipt.json()["lot_id"], "location_id": locations["A-01"],
        "damaged_qty": 1, "reason": "現場確認腐爛",
    })
    assert scrap.status_code == 201, scrap.text
    assert next(row for row in worker.get("/api/inventory/stock").json() if row["lot_id"] == receipt.json()["lot_id"])["qty"] == 2
    assert admin.post(f"/api/adjustments/{scrap.json()['id']}/review", json={"action": "APPROVE"}).status_code == 200
    assert next(row for row in worker.get("/api/inventory/stock").json() if row["lot_id"] == receipt.json()["lot_id"])["qty"] == 1


def test_count_check_all_is_atomic_and_only_creates_difference_request(clients):
    admin, worker = clients
    warehouse = next(row for row in worker.get("/api/master-data/warehouses").json() if row["code"] == "B")
    session = worker.post("/api/warehouse-counts", json={"warehouse_id": warehouse["id"]}).json()
    path = f"/api/warehouse-counts/{session['id']}/check-all"
    items = [
        {"item_id": item["id"], "observed_qty": item["original_qty"] - (1 if item["location_code"] == "B-03" else 0),
         "note": "現場少一籠" if item["location_code"] == "B-03" else ""}
        for item in session["items"]
    ]
    missing_reason = [{**item, "note": ""} for item in items]
    assert admin.post(path, json={"items": items}).status_code == 403
    assert worker.post(path, json={"items": items[:-1]}).status_code == 409
    assert worker.post(path, json={"items": [{**items[0], "observed_qty": 1.5}, *items[1:]]}).status_code == 422
    assert worker.post(path, json={"items": missing_reason}).status_code == 409
    assert all(item["checked_at"] is None for item in worker.get(f"/api/warehouse-counts/{session['id']}").json()["items"])
    assert admin.get("/api/adjustments/pending").json() == []
    assert worker.post(path, json={"items": items + [items[0]]}).status_code == 409
    checked = worker.post(path, json={"items": items})
    assert checked.status_code == 200, checked.text
    assert all(item["checked_at"] for item in checked.json()["items"])
    pending = admin.get("/api/adjustments/pending").json()
    assert len(pending) == 1 and pending[0]["kind"] == "COUNT"
    assert worker.post(path, json={"items": items}).status_code == 409


def test_count_difference_waits_for_review_and_legacy_migration(clients, tmp_path: Path):
    admin, worker = clients
    warehouse = next(row for row in worker.get("/api/master-data/warehouses").json() if row["code"] == "B")
    session = worker.post("/api/warehouse-counts", json={"warehouse_id": warehouse["id"]}).json()
    item = next(row for row in session["items"] if row["location_code"] == "B-03")
    response = worker.post(f"/api/warehouse-counts/{session['id']}/items/{item['id']}", json={
        "observed_qty": 0, "note": "現場找不到",
    })
    assert response.status_code == 200, response.text
    request_id = next(row for row in response.json()["items"] if row["id"] == item["id"])["adjustment_request_id"]
    assert request_id
    assert worker.post(f"/api/warehouse-counts/{session['id']}/items/{item['id']}/reopen").status_code == 409
    assert next(row for row in worker.get("/api/inventory/stock").json() if row["location_code"] == "B-03")["qty"] == 5
    assert admin.post(f"/api/adjustments/{request_id}/review", json={"action": "APPROVE"}).status_code == 200
    assert next(row for row in worker.get("/api/inventory/stock").json() if row["location_code"] == "B-03")["qty"] == 0
    reviewed_count = worker.get(f"/api/warehouse-counts/{session['id']}").json()
    assert next(row for row in reviewed_count["items"] if row["id"] == item["id"])["adjustment_status"] == "APPROVED"

    legacy = tmp_path / "legacy.db"
    schema = Path("backend/schema.sql").read_text(encoding="utf-8")
    schema = schema.split("CREATE TABLE warehouse_counts")[0].replace("  received_at TEXT,\n", "")
    with sqlite3.connect(legacy) as connection:
        connection.executescript(schema)
        connection.execute("INSERT INTO warehouses(code, name) VALUES ('A', '一號庫')")
    backup = backup_and_migrate(legacy)
    assert backup.exists()
    migrate_maintenance(legacy)
    with sqlite3.connect(legacy) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='warehouse_counts'").fetchone()
        assert "received_at" in {row[1] for row in connection.execute("PRAGMA table_info(lots)")}
        assert connection.execute("SELECT name FROM warehouses WHERE code='A'").fetchone()[0] == "一號庫"
