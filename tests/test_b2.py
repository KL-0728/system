from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.seed import seed_database


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "b2.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
    _sessions.clear()


def login(client: TestClient, username: str = "worker") -> None:
    result = client.post(
        "/api/auth/login", json={"username": username, "password": username + "1234"}
    )
    assert result.status_code == 200


def test_search_filters_and_empty_results_for_both_roles(client: TestClient):
    assert client.get("/api/inventory/stock").status_code == 401
    assert client.get("/api/inventory/movements", params={"lot_id": 1}).status_code == 401
    login(client)
    products = {row["name"]: row["id"] for row in client.get("/api/master-data/products").json()}
    locations = {row["code"]: row["id"] for row in client.get("/api/master-data/locations").json()}
    all_rows = client.get("/api/inventory/stock").json()
    assert len(all_rows) == 2
    assert {(row["lot_code"], row["location_code"], row["qty"], row["total_qty"])
            for row in all_rows} == {
        ("LOT-20260924-901", "B-03", 5, 5),
        ("LOT-20260924-902", "B-04", 3, 3),
    }
    assert all(row["age_days"] >= 0 and row["received_by"] == "倉管人員" for row in all_rows)
    filters = {"product_id": products["紅蘿蔔"], "lot_code": "901", "location_id": locations["B-03"]}
    matching = client.get("/api/inventory/stock", params=filters).json()
    assert len(matching) == 1 and matching[0]["lot_code"] == "LOT-20260924-901"
    assert client.get("/api/inventory/stock", params={"lot_code": "NO-SUCH-LOT"}).json() == []
    assert client.get("/api/inventory/stock", params={"location_id": locations["A-01"]}).json() == []
    assert client.get("/api/inventory/stock", params={"product_id": 0}).status_code == 422
    assert client.get("/api/inventory/movements", params={"lot_id": 0}).status_code == 422
    client.post("/api/auth/logout")
    login(client, "admin")
    assert len(client.get("/api/inventory/stock").json()) == 2
    assert len(client.get("/api/inventory/movements", params={"lot_id": all_rows[0]["lot_id"]}).json()) == 1


def test_transfer_outbound_totals_zero_row_and_history(client: TestClient):
    login(client)
    initial = client.get("/api/inventory/stock", params={"lot_code": "901"}).json()[0]
    locations = {row["code"]: row["id"] for row in client.get("/api/master-data/locations").json()}
    transfer = client.post("/api/outbound/transfers", json={
        "lot_id": initial["lot_id"], "from_location_id": locations["B-03"],
        "to_location_id": locations["A-01"], "qty": 2,
    })
    assert transfer.status_code == 201
    rows = client.get("/api/inventory/stock", params={"lot_code": "901"}).json()
    assert {(row["location_code"], row["qty"], row["total_qty"]) for row in rows} == {
        ("B-03", 3, 5), ("A-01", 2, 5),
    }
    filtered = client.get("/api/inventory/stock", params={"location_id": locations["A-01"]}).json()
    assert [(row["location_code"], row["qty"], row["total_qty"]) for row in filtered] == [("A-01", 2, 5)]
    outbound = client.post("/api/outbound", json={
        "lot_id": initial["lot_id"], "location_id": locations["B-03"], "qty": 3,
    })
    assert outbound.status_code == 201
    rows = client.get("/api/inventory/stock", params={"lot_code": "901"}).json()
    assert {(row["location_code"], row["qty"], row["total_qty"]) for row in rows} == {
        ("B-03", 0, 2), ("A-01", 2, 2),
    }
    history = client.get("/api/inventory/movements", params={"lot_id": initial["lot_id"]}).json()
    assert [row["kind"] for row in history] == ["OUTBOUND", "TRANSFER", "RECEIPT"]
    assert history[1]["from_location_code"] == "B-03"
    assert history[1]["to_location_code"] == "A-01"
    assert all(row["actor_name"] == "倉管人員" and row["created_at"].endswith("Z") for row in history)
    assert client.get("/api/inventory/movements", params={"lot_id": 99999}).json() == []


def test_inactive_location_stays_searchable_for_history(client: TestClient):
    login(client)
    with database.connect_database() as connection:
        location_id = connection.execute("SELECT id FROM locations WHERE code = 'B-03'").fetchone()[0]
        connection.execute("UPDATE locations SET is_active = 0 WHERE id = ?", (location_id,))
        connection.commit()
    rows = client.get("/api/inventory/stock", params={"location_id": location_id}).json()
    assert len(rows) == 1 and rows[0]["location_code"] == "B-03"
