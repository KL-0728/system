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
    path = tmp_path / "d1.db"
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


def carrot(client: TestClient) -> dict:
    return next(row for row in client.get("/api/stock-options/balances").json()
                if row["location_code"] == "B-03")


def request_payload(row: dict, **changes) -> dict:
    return {"lot_id": row["lot_id"], "location_id": row["location_id"],
            "kind": "COUNT", "observed_qty": 0, "reason": " 現場沒有找到貨 ", **changes}


def test_count_zero_persists_original_and_freezes_only_same_balance(client: TestClient):
    worker = login(client)
    row = carrot(client)
    before_movements = client.get("/api/inventory/movements", params={"lot_id": row["lot_id"]}).json()
    response = client.post("/api/adjustments", json=request_payload(row))
    assert response.status_code == 201
    record = response.json()
    assert record["status"] == "PENDING"
    assert record["original_qty"] == 5
    assert record["observed_qty"] == 0
    assert record["damaged_qty"] is None
    assert record["reason"] == "現場沒有找到貨"
    assert carrot(client)["qty"] == 5
    assert carrot(client)["has_pending"] is True
    assert client.get("/api/inventory/movements", params={"lot_id": row["lot_id"]}).json() == before_movements
    assert client.get("/api/adjustments/mine").json()[0] == record
    assert client.post("/api/adjustments", json=request_payload(row)).status_code == 409
    assert client.post("/api/outbound", json={"lot_id": row["lot_id"], "location_id": row["location_id"], "qty": 1}).status_code == 409
    with database.connect_database() as connection:
        stored = connection.execute("SELECT requested_by, original_qty, status FROM adjustment_requests WHERE id = ?", (record["id"],)).fetchone()
        assert stored["requested_by"] == worker["id"]
        assert stored["original_qty"] == 5
        assert stored["status"] == "PENDING"
        assert connection.execute("SELECT count(*) FROM adjustment_requests").fetchone()[0] == 1


def test_scrap_keeps_balance_and_rejects_overage(client: TestClient):
    login(client)
    row = carrot(client)
    payload = request_payload(row, kind="SCRAP", observed_qty=None, damaged_qty=1, reason="壓損一籠")
    assert client.post("/api/adjustments", json={**payload, "damaged_qty": 6}).status_code == 409
    assert carrot(client)["qty"] == 5
    assert client.get("/api/adjustments/mine").json() == []
    response = client.post("/api/adjustments", json=payload)
    assert response.status_code == 201
    assert response.json()["original_qty"] == 5
    assert response.json()["damaged_qty"] == 1
    assert response.json()["observed_qty"] is None
    assert carrot(client)["qty"] == 5
    assert client.get("/api/adjustments/mine").json()[0]["kind"] == "SCRAP"


@pytest.mark.parametrize("changes", [
    {"reason": "   "}, {"reason": ""}, {"observed_qty": -1},
    {"observed_qty": 1.5}, {"observed_qty": True},
    {"observed_qty": "2"}, {"observed_qty": 2**63},
    {"damaged_qty": 1}, {"kind": "SCRAP"},
    {"kind": "SCRAP", "observed_qty": None, "damaged_qty": 0},
    {"kind": "SCRAP", "observed_qty": None, "damaged_qty": 1.5},
    {"requested_by": 1},
])
def test_invalid_request_does_not_write(client: TestClient, changes: dict):
    login(client)
    row = carrot(client)
    assert client.post("/api/adjustments", json=request_payload(row, **changes)).status_code == 422
    assert client.get("/api/adjustments/mine").json() == []
    assert carrot(client)["qty"] == 5


def test_unknown_or_disabled_location_and_permissions(client: TestClient):
    row = {"lot_id": 1, "location_id": 1}
    assert client.post("/api/adjustments", json=request_payload(row)).status_code == 401
    assert client.get("/api/adjustments/mine").status_code == 401
    login(client, "admin")
    assert client.post("/api/adjustments", json=request_payload(row)).status_code == 403
    assert client.get("/api/adjustments/mine").status_code == 403
    login(client)
    row = carrot(client)
    assert client.post("/api/adjustments", json=request_payload(row, location_id=999999)).status_code == 409
    with database.connect_database() as connection:
        connection.execute("UPDATE locations SET is_active = 0 WHERE id = ?", (row["location_id"],))
        connection.commit()
    assert client.post("/api/adjustments", json=request_payload(row)).status_code == 409
    assert client.get("/api/adjustments/mine").json() == []


def test_mine_is_private_to_requesting_worker(client: TestClient):
    login(client)
    row = carrot(client)
    assert client.post("/api/adjustments", json=request_payload(row)).status_code == 201
    with database.connect_database() as connection:
        connection.execute("INSERT INTO users (username, password_hash, display_name, role) SELECT 'worker2', password_hash, '另一位倉管', role FROM users WHERE username='worker'")
        connection.commit()
    client.post("/api/auth/logout")
    response = client.post("/api/auth/login", json={"username": "worker2", "password": "worker1234"})
    assert response.status_code == 200
    assert client.get("/api/adjustments/mine").json() == []
