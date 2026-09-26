"""Regression checks for master-data and session integrity."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.seed import seed_database


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "hardening.db"
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    database.initialize_database()
    seed_database(path)
    _sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
    _sessions.clear()


def login(client: TestClient, username: str) -> None:
    assert client.post("/api/auth/login", json={
        "username": username, "password": username + "1234",
    }).status_code == 200


def test_shortage_unit_cannot_change_after_history(client: TestClient):
    login(client, "admin")
    created = client.post("/api/master-data/products", json={
        "name": "試驗品項", "unit": "箱", "min_qty": 0, "target_qty": 2,
    })
    assert created.status_code == 201
    product_id = created.json()["id"]
    login(client, "worker")
    assert client.post("/api/shortages", json={"product_id": product_id, "qty": 3}).status_code == 201
    login(client, "admin")
    changed = client.put(f"/api/master-data/products/{product_id}", json={
        "name": "試驗品項", "unit": "公斤", "min_qty": 0, "target_qty": 2,
    })
    assert changed.status_code == 409
    login(client, "worker")
    assert client.get("/api/shortages").json()[0]["unit"] == "箱"


def test_pending_count_blocks_disable_and_legacy_inactive_gain(client: TestClient):
    login(client, "worker")
    balance = next(row for row in client.get("/api/stock-options/balances").json()
                   if row["location_code"] == "B-03")
    location_id = balance["location_id"]
    assert client.post("/api/outbound", json={
        "lot_id": balance["lot_id"], "location_id": location_id, "qty": balance["qty"],
    }).status_code == 201
    request = client.post("/api/adjustments", json={
        "kind": "COUNT", "lot_id": balance["lot_id"], "location_id": location_id,
        "observed_qty": 2, "reason": "盤盈測試",
    })
    assert request.status_code == 201
    login(client, "admin")
    location = next(row for row in client.get("/api/master-data/locations").json() if row["id"] == location_id)
    payload = {"warehouse_id": location["warehouse_id"], "code": location["code"], "is_active": False}
    disabled = client.put(f"/api/master-data/locations/{location_id}", json=payload)
    assert disabled.status_code == 409
    assert "待審" in disabled.json()["detail"]
    with database.connect_database() as connection:
        connection.execute("UPDATE locations SET is_active = 0 WHERE id = ?", (location_id,))
        connection.commit()
    approval = client.post(f"/api/adjustments/{request.json()['id']}/review", json={"action": "APPROVE"})
    assert approval.status_code == 409
    assert client.get(f"/api/adjustments/{request.json()['id']}").json()["status"] == "PENDING"
    assert client.post(f"/api/adjustments/{request.json()['id']}/review", json={
        "action": "REJECT", "review_note": "儲位已停用",
    }).status_code == 200


def test_invalid_bounds_and_location_code_return_client_errors(client: TestClient):
    login(client, "admin")
    huge = 10 ** 30
    assert client.post("/api/master-data/products", json={
        "name": "大數測試", "unit": "箱", "min_qty": huge, "target_qty": huge,
    }).status_code == 422
    warehouse_id = client.get("/api/master-data/warehouses").json()[0]["id"]
    for code in ("INVALID-CODE", "A-00", "A-100"):
        assert client.post("/api/master-data/locations", json={"warehouse_id": warehouse_id, "code": code}).status_code == 422
    assert client.post("/api/master-data/locations", json={"warehouse_id": warehouse_id, "code": "B-77"}).status_code == 409
    assert client.get(f"/api/stock-options/lots?product_id={huge}").status_code == 422
    assert client.get(f"/api/stock-options/balances?lot_id={huge}").status_code == 422


def test_login_rotates_existing_token_and_session_expires(client: TestClient):
    login(client, "worker")
    old_token = client.cookies.get("inventory_session")
    assert old_token and old_token in _sessions
    login(client, "admin")
    assert old_token not in _sessions
    token = client.cookies.get("inventory_session")
    assert token and token in _sessions
    user_id, _ = _sessions[token]
    _sessions[token] = (user_id, 0)
    assert client.get("/api/auth/me").status_code == 401
    assert token not in _sessions
