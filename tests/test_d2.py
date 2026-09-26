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
    path = tmp_path / "d2.db"
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


def balance(client: TestClient, location_code: str = "B-03") -> dict:
    return next(row for row in client.get("/api/stock-options/balances?positive_only=false").json()
                if row["location_code"] == location_code)


def submit_count(client: TestClient, observed: int = 0) -> dict:
    row = balance(client)
    response = client.post("/api/adjustments", json={
        "lot_id": row["lot_id"], "location_id": row["location_id"],
        "kind": "COUNT", "observed_qty": observed, "reason": "現場盤點",
    })
    assert response.status_code == 201
    return response.json()


def review(client: TestClient, request_id: int, action: str = "APPROVE", note: str = ""):
    return client.post(f"/api/adjustments/{request_id}/review", json={"action": action, "review_note": note})


def test_admin_reads_pending_detail_and_count_loss_approves_once(client: TestClient):
    worker = login(client)
    request = submit_count(client)
    login(client, "admin")
    pending = client.get("/api/adjustments/pending").json()
    assert len(pending) == 1
    assert pending[0]["requester_name"] == worker["display_name"]
    assert pending[0]["original_qty"] == 5
    assert pending[0]["observed_qty"] == 0
    assert pending[0]["difference"] == -5
    assert pending[0]["current_qty"] == 5
    assert client.get(f"/api/adjustments/{request['id']}").json() == pending[0]
    response = review(client, request["id"], note="同意盤差")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "APPROVED"
    assert result["delta"] == -5
    assert result["new_qty"] == 0
    assert result["movement_id"] is not None
    assert result["review_note"] == "同意盤差"
    assert result["reviewed_at"].endswith("Z")
    assert client.get("/api/adjustments/pending").json() == []
    detail = client.get(f"/api/adjustments/{request['id']}").json()
    assert detail["status"] == "APPROVED"
    assert detail["movement_id"] == result["movement_id"]
    assert detail["current_qty"] == 0
    assert review(client, request["id"]).status_code == 409
    with database.connect_database() as connection:
        movement = connection.execute("SELECT * FROM stock_movements WHERE id = ?", (result["movement_id"],)).fetchone()
        assert movement["kind"] == "COUNT_LOSS"
        assert movement["qty"] == 5
        assert movement["from_location_id"] == request["location_id"]
        assert movement["adjustment_request_id"] == request["id"]
        assert movement["actor_id"] == result["reviewed_by"]
        assert connection.execute("SELECT count(*) FROM stock_movements WHERE kind='RECEIPT'").fetchone()[0] == 2
    login(client)
    assert balance(client)["qty"] == 0
    assert balance(client)["has_pending"] is False
    assert client.get("/api/adjustments/mine").json()[0]["status"] == "APPROVED"


@pytest.mark.parametrize("observed,expected_kind,expected_delta", [
    (7, "COUNT_GAIN", 2), (5, None, 0),
])
def test_count_gain_or_zero_difference(client: TestClient, observed, expected_kind, expected_delta):
    login(client)
    request = submit_count(client, observed)
    login(client, "admin")
    result = review(client, request["id"]).json()
    assert result["status"] == "APPROVED"
    assert result["delta"] == expected_delta
    assert result["new_qty"] == observed
    with database.connect_database() as connection:
        movements = connection.execute(
            "SELECT kind, qty, to_location_id FROM stock_movements WHERE adjustment_request_id = ?",
            (request["id"],),
        ).fetchall()
        if expected_kind:
            assert len(movements) == 1
            assert movements[0]["kind"] == expected_kind
            assert movements[0]["qty"] == expected_delta
            assert movements[0]["to_location_id"] == request["location_id"]
        else:
            assert movements == []
            assert result["movement_id"] is None


def test_scrap_approval_and_rejection(client: TestClient):
    login(client)
    row = balance(client)
    response = client.post("/api/adjustments", json={
        "lot_id": row["lot_id"], "location_id": row["location_id"],
        "kind": "SCRAP", "damaged_qty": 1, "reason": "壓損",
    })
    assert response.status_code == 201
    request_id = response.json()["id"]
    login(client, "admin")
    result = review(client, request_id).json()
    assert result["new_qty"] == 4
    assert result["delta"] == -1
    with database.connect_database() as connection:
        movement = connection.execute("SELECT kind, qty, from_location_id FROM stock_movements WHERE adjustment_request_id = ?", (request_id,)).fetchone()
        assert (movement["kind"], movement["qty"], movement["from_location_id"]) == ("SCRAP", 1, row["location_id"])
    login(client)
    rejected = submit_count(client, 3)
    login(client, "admin")
    assert review(client, rejected["id"], "REJECT", "   ").status_code == 422
    assert client.get(f"/api/adjustments/{rejected['id']}").json()["status"] == "PENDING"
    result = review(client, rejected["id"], "REJECT", "數字需重查").json()
    assert result["status"] == "REJECTED"
    assert result["new_qty"] == 4
    assert result["delta"] == 0
    assert result["movement_id"] is None
    assert review(client, rejected["id"], "REJECT", "重複").status_code == 409
    login(client)
    assert balance(client)["has_pending"] is False
    assert submit_count(client, 4)["original_qty"] == 4


def test_reviewed_history_survives_refresh_and_worker_sees_rejection_reason(client: TestClient):
    assert client.get("/api/adjustments/reviewed").status_code == 401
    login(client)
    first = submit_count(client, 5)
    assert client.get("/api/adjustments/reviewed").status_code == 403
    login(client, "admin")
    assert client.get("/api/adjustments/reviewed").json() == []
    assert review(client, first["id"], note="數量核對無誤").status_code == 200
    login(client)
    second = submit_count(client, 4)
    login(client, "admin")
    assert review(client, second["id"], "REJECT", "請重新盤點").status_code == 200
    assert client.get("/api/adjustments/pending").json() == []
    history = client.get("/api/adjustments/reviewed").json()
    assert [row["id"] for row in history] == [second["id"], first["id"]]
    assert [row["status"] for row in history] == ["REJECTED", "APPROVED"]
    assert history[0]["review_note"] == "請重新盤點"
    assert history[1]["review_note"] == "數量核對無誤"
    login(client)
    mine = client.get("/api/adjustments/mine").json()
    assert [row["id"] for row in mine] == [second["id"], first["id"]]
    assert mine[0]["review_note"] == "請重新盤點"
    assert mine[0]["reviewer_name"] and mine[0]["reviewed_at"].endswith("Z")
    assert mine[1]["review_note"] == "數量核對無誤"


def test_permission_self_review_and_invalid_input(client: TestClient):
    assert client.get("/api/adjustments/pending").status_code == 401
    assert client.get("/api/adjustments/1").status_code == 401
    assert review(client, 1).status_code == 401
    login(client)
    request = submit_count(client)
    assert client.get("/api/adjustments/pending").status_code == 403
    assert client.get(f"/api/adjustments/{request['id']}").status_code == 403
    assert review(client, request["id"]).status_code == 403
    login(client, "admin")
    assert client.get("/api/adjustments/999999").status_code == 404
    assert review(client, 999999).status_code == 409
    for payload in [{"action": "REJECT"}, {"action": "APPROVE", "reviewed_by": 1},
                    {"action": "UNKNOWN"}, {"action": "REJECT", "review_note": " "},
                    {"action": "APPROVE", "review_note": "字" * 501}]:
        assert client.post(f"/api/adjustments/{request['id']}/review", json=payload).status_code == 422
    assert client.get(f"/api/adjustments/{request['id']}").json()["status"] == "PENDING"
    with database.connect_database() as connection:
        connection.execute("""INSERT INTO adjustment_requests
            (kind, lot_id, location_id, original_qty, observed_qty, reason, requested_by)
            SELECT 'COUNT', b.lot_id, b.location_id, b.qty, b.qty, '管理者舊申請', u.id
            FROM stock_balances b JOIN users u ON u.username='admin'
            WHERE b.lot_id <> ? LIMIT 1""", (request["lot_id"],))
        own_id = connection.execute("SELECT max(id) FROM adjustment_requests").fetchone()[0]
        connection.commit()
    assert review(client, own_id).status_code == 409
    assert client.get(f"/api/adjustments/{own_id}").json()["status"] == "PENDING"


def test_stale_balance_and_movement_failure_roll_back(client: TestClient):
    login(client)
    request = submit_count(client, 3)
    login(client, "admin")
    with database.connect_database() as connection:
        connection.execute("UPDATE stock_balances SET qty = 4 WHERE lot_id = ? AND location_id = ?", (request["lot_id"], request["location_id"]))
        connection.commit()
    assert review(client, request["id"]).status_code == 409
    assert client.get(f"/api/adjustments/{request['id']}").json()["status"] == "PENDING"
    with database.connect_database() as connection:
        connection.execute("UPDATE stock_balances SET qty = 5 WHERE lot_id = ? AND location_id = ?", (request["lot_id"], request["location_id"]))
        connection.commit()
    with patch("backend.services.adjustment_service.record_movement", side_effect=sqlite3.IntegrityError("forced")):
        with pytest.raises(sqlite3.IntegrityError):
            review(client, request["id"])
    detail = client.get(f"/api/adjustments/{request['id']}").json()
    assert detail["status"] == "PENDING"
    assert detail["current_qty"] == 5
    assert detail["movement_id"] is None
    assert review(client, request["id"]).json()["new_qty"] == 3


def test_pending_freezes_source_and_existing_target_until_closed(client: TestClient):
    login(client)
    row = balance(client)
    target = next(location for location in client.get("/api/stock-options/locations").json()
                  if location["location_code"] == "B-04")
    move = {"lot_id": row["lot_id"], "from_location_id": row["location_id"],
            "to_location_id": target["location_id"], "qty": 1}
    source_request = submit_count(client, 5)
    assert client.post("/api/outbound/transfers", json=move).status_code == 409
    login(client, "admin")
    assert review(client, source_request["id"]).status_code == 200
    login(client)
    assert client.post("/api/outbound/transfers", json=move).status_code == 201
    target_request = client.post("/api/adjustments", json={
        "lot_id": row["lot_id"], "location_id": target["location_id"],
        "kind": "COUNT", "observed_qty": 1, "reason": "目標盤點",
    }).json()
    assert client.post("/api/outbound/transfers", json=move).status_code == 409
    login(client, "admin")
    assert review(client, target_request["id"], "REJECT", "重查").status_code == 200
    login(client)
    assert client.post("/api/outbound/transfers", json=move).status_code == 201
