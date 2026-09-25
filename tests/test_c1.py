from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions
from backend.main import app
from backend.seed import seed_database


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "c1.db"
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


def carrot(client):
    return next(row for row in client.get("/api/stock-options/balances").json() if row["location_code"] == "B-03")


def payload(row, qty=2):
    return {"lot_id": row["lot_id"], "location_id": row["location_id"], "qty": qty, "note": " 測試出庫 "}


def assert_unchanged(client):
    assert carrot(client)["qty"] == 5
    assert client.get("/api/outbound").json() == []


def test_outbound_persists_actor_history_and_zero_balance(client):
    user = login(client)
    row = carrot(client)
    response = client.post("/api/outbound", json=payload(row))
    assert response.status_code == 201
    assert response.json()["qty"] == 3
    assert carrot(client)["qty"] == 3
    records = client.get("/api/outbound", params={"lot_id": row["lot_id"], "location_id": row["location_id"]}).json()
    assert len(records) == 1
    assert records[0]["movement_id"] == response.json()["movement_id"]
    assert records[0]["qty"] == 2
    assert records[0]["actor_name"] == user["display_name"]
    assert records[0]["note"] == "測試出庫"
    assert records[0]["created_at"].endswith("Z")
    assert client.get("/api/outbound?lot_id=999999").json() == []
    assert client.post("/api/outbound", json=payload(row, 3)).json()["qty"] == 0
    balances = client.get("/api/stock-options/balances?positive_only=false").json()
    assert next(item for item in balances if item["lot_id"] == row["lot_id"])["qty"] == 0
    assert client.post("/api/outbound", json=payload(row, 1)).status_code == 409
    with database.connect_database() as connection:
        assert connection.execute("SELECT count(*) FROM stock_movements WHERE kind='OUTBOUND'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM stock_movements WHERE kind='RECEIPT'").fetchone()[0] == 2
        movement = connection.execute("SELECT * FROM stock_movements WHERE kind='OUTBOUND' LIMIT 1").fetchone()
        assert movement["actor_id"] == user["id"]
        assert movement["to_location_id"] is None


@pytest.mark.parametrize("qty", [0, -1, 1.5, True, "2", 2**63])
def test_rejects_invalid_quantity_without_writing(client, qty):
    login(client)
    assert client.post("/api/outbound", json=payload(carrot(client), qty)).status_code == 422
    assert_unchanged(client)


def test_overdraw_unknown_balance_and_invalid_fields(client):
    login(client)
    data = payload(carrot(client))
    for changes, status in [({"qty": 6}, 409), ({"location_id": 99999}, 409),
                            ({"lot_id": 0}, 422), ({"note": "字" * 501}, 422),
                            ({"actor_id": 1}, 422)]:
        assert client.post("/api/outbound", json={**data, **changes}).status_code == status
        assert_unchanged(client)


def test_pending_only_freezes_same_lot_and_location(client):
    user = login(client)
    row = carrot(client)
    with database.connect_database() as connection:
        connection.execute("""INSERT INTO adjustment_requests
            (kind, lot_id, location_id, original_qty, observed_qty, reason, requested_by)
            VALUES ('COUNT', ?, ?, 5, 4, '測試待審', ?)""", (row["lot_id"], row["location_id"], user["id"]))
        connection.commit()
    response = client.post("/api/outbound", json=payload(row))
    assert response.status_code == 409
    assert "待審" in response.json()["detail"]
    assert carrot(client)["has_pending"] is True
    assert_unchanged(client)
    # Another lot at the same location is not frozen.
    with database.connect_database() as connection:
        other_lot = connection.execute("SELECT id FROM lots WHERE id <> ?", (row["lot_id"],)).fetchone()[0]
        connection.execute("INSERT INTO stock_balances VALUES (?, ?, 1)", (other_lot, row["location_id"]))
        connection.commit()
    assert client.post("/api/outbound", json={**payload(row, 1), "lot_id": other_lot}).status_code == 201


def test_movement_failure_rolls_back_deduction(client):
    login(client)
    data = payload(carrot(client))
    with patch("backend.services.outbound_service.record_movement", side_effect=sqlite3.IntegrityError("forced failure")):
        with pytest.raises(sqlite3.IntegrityError):
            client.post("/api/outbound", json=data)
    assert_unchanged(client)


def test_requires_worker_and_authenticated_read(client):
    data = {"lot_id": 1, "location_id": 1, "qty": 1}
    assert client.post("/api/outbound", json=data).status_code == 401
    assert client.get("/api/outbound").status_code == 401
    login(client, "admin")
    assert client.post("/api/outbound", json=data).status_code == 403
    assert client.get("/api/outbound").status_code == 200
    assert_unchanged(client)
