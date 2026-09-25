from datetime import timedelta
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.schemas.inbound import taiwan_today
from backend.seed import seed_database


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "b1.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as client:
        yield client
    _sessions.clear()


def login(client, username="worker"):
    response = client.post("/api/auth/login", json={"username": username, "password": username + "1234"})
    assert response.status_code == 200
    return response.json()


def ids(client):
    products = {row["name"]: row["id"] for row in client.get("/api/master-data/products").json()}
    locations = {row["code"]: row["id"] for row in client.get("/api/master-data/locations").json()}
    return products, locations


def payload(client, qty=10, received_date="2026-09-25"):
    products, locations = ids(client)
    return {"product_id": products["紅蘿蔔"], "location_id": locations["A-01"],
            "qty": qty, "received_date": received_date, "note": " 課堂入庫 "}


def counts():
    with database.connect_database() as connection:
        return tuple(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                     for table in ("lots", "stock_balances", "stock_movements"))


def test_inbound_creates_lot_balance_and_receipt_in_one_go(client):
    user = login(client)
    data = payload(client)
    response = client.post("/api/inventory/inbound", json=data)
    assert response.status_code == 201
    result = response.json()
    assert result["lot_code"] == "LOT-20260925-001"
    assert result["qty"] == 10
    # Readable after a fresh request (refresh), via the shared A3 menu and B1 records.
    balance = next(row for row in client.get("/api/stock-options/balances").json() if row["lot_id"] == result["lot_id"])
    assert (balance["location_code"], balance["qty"], balance["received_date"]) == ("A-01", 10, "2026-09-25")
    records = client.get("/api/inventory/inbound", params={"lot_id": result["lot_id"]}).json()
    assert len(records) == 1
    assert records[0]["movement_id"] == result["movement_id"]
    assert records[0]["actor_name"] == user["display_name"]
    assert records[0]["note"] == "課堂入庫"
    assert records[0]["created_at"].endswith("Z")
    with database.connect_database() as connection:
        lot = connection.execute("SELECT * FROM lots WHERE id = ?", (result["lot_id"],)).fetchone()
        movement = connection.execute("SELECT * FROM stock_movements WHERE id = ?", (result["movement_id"],)).fetchone()
    assert lot["created_by"] == user["id"]
    assert (movement["kind"], movement["qty"], movement["from_location_id"]) == ("RECEIPT", 10, None)
    assert movement["to_location_id"] == data["location_id"] and movement["actor_id"] == user["id"]


def test_lot_code_increments_per_date_and_skips_seed_numbers(client):
    login(client)
    first = client.post("/api/inventory/inbound", json=payload(client, 1)).json()["lot_code"]
    second = client.post("/api/inventory/inbound", json=payload(client, 2)).json()["lot_code"]
    seeded_day = client.post("/api/inventory/inbound", json=payload(client, 3, "2026-09-24")).json()["lot_code"]
    assert (first, second, seeded_day) == ("LOT-20260925-001", "LOT-20260925-002", "LOT-20260924-903")


@pytest.mark.parametrize("qty", [0, -1, 1.5, True, "2", 2**63])
def test_rejects_invalid_quantity_without_writing(client, qty):
    login(client)
    before = counts()
    assert client.post("/api/inventory/inbound", json=payload(client, qty)).status_code == 422
    assert counts() == before


@pytest.mark.parametrize("received_date", ["2026-02-30", "2026/09/25", "20260925", "", "future"])
def test_rejects_invalid_date_without_writing(client, received_date):
    login(client)
    if received_date == "future":
        received_date = (taiwan_today() + timedelta(days=1)).isoformat()
    before = counts()
    assert client.post("/api/inventory/inbound", json=payload(client, received_date=received_date)).status_code == 422
    assert counts() == before


def test_rejects_inactive_or_unknown_location_and_product(client):
    login(client)
    data = payload(client)
    with database.connect_database() as connection:
        connection.execute("UPDATE locations SET is_active = 0 WHERE code = 'A-02'")
        inactive_location = connection.execute("SELECT id FROM locations WHERE code = 'A-02'").fetchone()[0]
        connection.execute("UPDATE products SET is_active = 0 WHERE name = '青花菜'")
        inactive_product = connection.execute("SELECT id FROM products WHERE name = '青花菜'").fetchone()[0]
        connection.commit()
    before = counts()
    for changes, detail in [({"location_id": inactive_location}, "停用"), ({"location_id": 99999}, "找不到"),
                            ({"product_id": inactive_product}, "停用"), ({"product_id": 99999}, "找不到")]:
        response = client.post("/api/inventory/inbound", json={**data, **changes})
        assert response.status_code == 409
        assert detail in response.json()["detail"]
        assert counts() == before
    for changes in [{"note": "字" * 501}, {"actor_id": 1}, {"lot_code": "LOT-X"}, {"product_id": 0}]:
        assert client.post("/api/inventory/inbound", json={**data, **changes}).status_code == 422
        assert counts() == before


def test_movement_failure_rolls_back_lot_and_balance(client):
    login(client)
    data = payload(client)
    before = counts()
    with patch("backend.services.inbound_service.record_movement", side_effect=sqlite3.IntegrityError("forced failure")):
        with pytest.raises(sqlite3.IntegrityError):
            client.post("/api/inventory/inbound", json=data)
    assert counts() == before


def test_requires_worker_to_write_and_login_to_read(client):
    data = {"product_id": 1, "location_id": 1, "qty": 1, "received_date": "2026-09-25"}
    assert client.post("/api/inventory/inbound", json=data).status_code == 401
    assert client.get("/api/inventory/inbound").status_code == 401
    login(client, "admin")
    before = counts()
    assert client.post("/api/inventory/inbound", json=data).status_code == 403
    assert len(client.get("/api/inventory/inbound").json()) == 2  # the two seed receipts
    assert counts() == before
