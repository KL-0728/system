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
    path = tmp_path / "c2.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
    _sessions.clear()


def login(client, username="worker"):
    response = client.post("/api/auth/login", json={"username": username, "password": username + "1234"})
    assert response.status_code == 200
    return response.json()


def setup(client):
    source = next(row for row in client.get("/api/stock-options/balances").json() if row["location_code"] == "B-03")
    target = next(row for row in client.get("/api/stock-options/locations").json() if row["location_code"] == "B-04")
    return {"lot_id": source["lot_id"], "from_location_id": source["location_id"],
            "to_location_id": target["location_id"], "qty": 2}


def balances(client, lot_id):
    return {row["location_id"]: row["qty"] for row in client.get(
        "/api/stock-options/balances", params={"lot_id": lot_id, "positive_only": False}
    ).json()}


def test_transfer_total_history_and_zero_row(client):
    actor = login(client)
    data = setup(client)
    before = balances(client, data["lot_id"])
    response = client.post("/api/outbound/transfers", json=data)
    assert response.status_code == 201
    assert response.json()["from_qty"] == 3
    assert response.json()["to_qty"] == 2
    after = balances(client, data["lot_id"])
    assert sum(after.values()) == sum(before.values()) == 5
    assert after[data["from_location_id"]] == 3
    assert after[data["to_location_id"]] == 2
    record = client.get("/api/outbound/transfers", params={"lot_id": data["lot_id"]}).json()[0]
    assert record["movement_id"] == response.json()["movement_id"]
    assert record["actor_name"] == actor["display_name"]
    assert record["created_at"].endswith("Z")
    assert client.post("/api/outbound/transfers", json={**data, "qty": 3}).json()["from_qty"] == 0
    assert balances(client, data["lot_id"])[data["from_location_id"]] == 0
    assert client.get("/api/outbound/transfers", params={"lot_id": 999999}).json() == []


@pytest.mark.parametrize("change,status", [
    ({"qty": 6}, 409), ({"qty": 0}, 422), ({"qty": -1}, 422),
    ({"qty": 1.5}, 422), ({"qty": True}, 422), ({"qty": 2**63}, 422),
    ({"to_location_id": 99999}, 409), ({"lot_id": 0}, 422),
    ({"actor_id": 1}, 422),
])
def test_rejection_keeps_stock_and_history(client, change, status):
    login(client)
    data = setup(client)
    before = balances(client, data["lot_id"])
    assert client.post("/api/outbound/transfers", json={**data, **change}).status_code == status
    assert balances(client, data["lot_id"]) == before
    assert client.get("/api/outbound/transfers").json() == []


def test_same_location_disabled_target_and_permissions(client):
    assert client.post("/api/outbound/transfers", json={}).status_code == 401
    assert client.get("/api/outbound/transfers").status_code == 401
    login(client, "admin")
    data = setup(client)
    assert client.post("/api/outbound/transfers", json=data).status_code == 403
    assert client.get("/api/outbound/transfers").status_code == 200
    login(client)
    assert client.post("/api/outbound/transfers", json={**data, "to_location_id": data["from_location_id"]}).status_code == 409
    with database.connect_database() as connection:
        connection.execute("UPDATE locations SET is_active = 0 WHERE id = ?", (data["to_location_id"],))
        connection.commit()
    assert client.post("/api/outbound/transfers", json=data).status_code == 409
    assert client.get("/api/outbound/transfers").json() == []


@pytest.mark.parametrize("freeze_target", [False, True])
def test_pending_source_or_existing_target_is_frozen(client, freeze_target):
    actor = login(client)
    data = setup(client)
    with database.connect_database() as connection:
        if freeze_target:
            connection.execute("INSERT INTO stock_balances (lot_id, location_id, qty) VALUES (?, ?, 0)",
                               (data["lot_id"], data["to_location_id"]))
        frozen_id = data["to_location_id"] if freeze_target else data["from_location_id"]
        connection.execute("""INSERT INTO adjustment_requests
            (kind, lot_id, location_id, original_qty, observed_qty, reason, requested_by)
            VALUES ('COUNT', ?, ?, ?, 1, '待審測試', ?)""",
            (data["lot_id"], frozen_id, 0 if freeze_target else 5, actor["id"]))
        connection.commit()
    before = balances(client, data["lot_id"])
    assert client.post("/api/outbound/transfers", json=data).status_code == 409
    assert balances(client, data["lot_id"]) == before
    assert client.get("/api/outbound/transfers").json() == []
