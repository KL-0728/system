import csv
from datetime import timedelta
from io import StringIO
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.migrate_extras import migrate_extras
from backend.schemas.inbound import taiwan_today
from backend.seed import seed_database


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "extras.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
    _sessions.clear()


def login(client: TestClient, username: str):
    response = client.post("/api/auth/login", json={
        "username": username, "password": username + "1234",
    })
    assert response.status_code == 200


def test_shortage_demand_is_persistent_separate_from_stock_and_report(client: TestClient):
    assert client.post("/api/shortages", json={"product_id": 1, "qty": 3}).status_code == 401
    login(client, "worker")
    with database.connect_database() as connection:
        product_id = connection.execute(
            "INSERT INTO products (name, unit, min_qty, target_qty) VALUES ('零庫存品項', '箱', 1, 4)"
        ).lastrowid
        before_stock = connection.execute("SELECT SUM(qty) FROM stock_balances").fetchone()[0]
        before_movements = connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0]
        connection.commit()
    for qty in (0, -1, 1.5, True):
        assert client.post("/api/shortages", json={"product_id": product_id, "qty": qty}).status_code == 422
    created = client.post("/api/shortages", json={
        "product_id": product_id, "qty": 3, "note": "  客人詢問  ",
    })
    assert created.status_code == 201
    assert created.json()["note"] == "客人詢問"
    assert client.get("/api/shortages").json()[0]["qty"] == 3
    with database.connect_database() as connection:
        assert connection.execute("SELECT SUM(qty) FROM stock_balances").fetchone()[0] == before_stock
        assert connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == before_movements
    assert client.get("/api/reports").status_code == 403
    client.post("/api/auth/logout")
    login(client, "admin")
    assert client.post("/api/shortages", json={"product_id": product_id, "qty": 1}).status_code == 403
    report = client.get("/api/reports").json()
    product = next(row for row in report["products"] if row["product_id"] == product_id)
    assert product["current_qty"] == 0
    assert product["outbound_30d"] == 0
    assert product["shortage_demand_qty"] == 3
    assert report["summary"]["shortage_demand_count"] == 1
    assert report["shortage_demands"][0]["id"] == created.json()["id"]


def test_expiry_is_admin_entered_and_search_labels_date(client: TestClient):
    login(client, "worker")
    lot = client.get("/api/inventory/stock", params={"lot_code": "901"}).json()[0]
    assert lot["expires_on"] is None and lot["expiry_status"] == "未提供"
    path = f"/api/inventory/lots/{lot['lot_id']}/expiry"
    assert client.put(path, json={"expires_on": "2026-09-30"}).status_code == 403
    client.post("/api/auth/logout")
    login(client, "admin")
    assert client.put(path, json={"expires_on": "2026-02-30"}).status_code == 422
    assert client.put("/api/inventory/lots/999999/expiry", json={"expires_on": None}).status_code == 404
    upcoming = (taiwan_today() + timedelta(days=7)).isoformat()
    assert client.put(path, json={"expires_on": upcoming}).status_code == 200
    row = client.get("/api/inventory/stock", params={"lot_code": "901"}).json()[0]
    assert row["expires_on"] == upcoming and row["expiry_status"] == "即將到期" and row["qty"] == 5
    overdue = (taiwan_today() - timedelta(days=1)).isoformat()
    assert client.put(path, json={"expires_on": overdue}).status_code == 200
    assert client.get("/api/inventory/stock", params={"lot_code": "901"}).json()[0]["expiry_status"] == "已到期"
    assert client.put(path, json={"expires_on": None}).status_code == 200
    assert client.get("/api/inventory/stock", params={"lot_code": "901"}).json()[0]["expiry_status"] == "未提供"


def test_csv_export_uses_filters_and_escapes_spreadsheet_formulas(client: TestClient):
    assert client.get("/api/inventory/stock.csv").status_code == 401
    login(client, "worker")
    with database.connect_database() as connection:
        connection.execute("UPDATE products SET name = '=2+2' WHERE name = '紅蘿蔔'")
        connection.commit()
    response = client.get("/api/inventory/stock.csv", params={"lot_code": "901"})
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.startswith("\ufeff")
    rows = list(csv.reader(StringIO(response.text.lstrip("\ufeff"))))
    assert len(rows) == 2
    assert rows[0][:4] == ["品項", "單位", "批次碼", "儲位"]
    assert rows[1][0] == "'=2+2"
    assert rows[1][2] == "LOT-20260924-901" and rows[1][5] == "5"
    assert list(csv.reader(StringIO(client.get("/api/inventory/stock.csv", params={"lot_code": "NOPE"}).text.lstrip("\ufeff")))) == [rows[0]]


def test_migration_preserves_legacy_rows_and_is_idempotent(tmp_path: Path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY);
            CREATE TABLE products (id INTEGER PRIMARY KEY);
            CREATE TABLE lots (id INTEGER PRIMARY KEY, lot_code TEXT);
            CREATE TABLE stock_balances (lot_id INTEGER, location_id INTEGER, qty INTEGER);
            INSERT INTO lots (lot_code) VALUES ('KEPT-LOT');
            INSERT INTO stock_balances VALUES (1, 7, 5);
        """)
    migrate_extras(path)
    migrate_extras(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT lot_code, expires_on FROM lots").fetchone() == ("KEPT-LOT", None)
        assert connection.execute("SELECT qty FROM stock_balances").fetchone()[0] == 5
        assert connection.execute("SELECT COUNT(*) FROM shortage_demands").fetchone()[0] == 0
