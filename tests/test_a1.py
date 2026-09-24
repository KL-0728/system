from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions, require_admin
from backend.main import app
from backend.seed import seed_database
from backend.services.auth_service import AuthenticatedUser
from backend.services.stock_service import (
    StockError,
    change_balance,
    ensure_no_pending,
    get_balance,
    stock_transaction,
)


@pytest.fixture()
def seeded_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "inventory.db"
    connection = sqlite3.connect(path)
    connection.executescript(Path("backend/schema.sql").read_text(encoding="utf-8"))
    connection.close()
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    seed_database(path)
    _sessions.clear()
    return path


def test_seed_is_idempotent_and_preserves_existing_data(seeded_database: Path) -> None:
    connection = sqlite3.connect(seeded_database)
    original_hash = connection.execute(
        "SELECT password_hash FROM users WHERE username = 'admin'"
    ).fetchone()[0]
    connection.execute("UPDATE products SET min_qty = 7 WHERE name = '紅蘿蔔'")
    connection.commit()
    connection.close()

    seed_database(seeded_database)

    connection = sqlite3.connect(seeded_database)
    assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 2
    assert connection.execute("SELECT count(*) FROM warehouses").fetchone()[0] == 2
    assert connection.execute("SELECT count(*) FROM locations").fetchone()[0] == 5
    assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == 2
    assert connection.execute(
        "SELECT count(*) FROM products WHERE name = '甘藍菜'"
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT min_qty FROM products WHERE name = '紅蘿蔔'"
    ).fetchone()[0] == 7
    assert connection.execute(
        "SELECT password_hash FROM users WHERE username = 'admin'"
    ).fetchone()[0] == original_hash
    connection.close()


def test_login_lists_and_logout(seeded_database: Path) -> None:
    with TestClient(app) as client:
        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/master-data/products").status_code == 401
        assert client.post(
            "/api/auth/login", json={"username": "worker", "password": "wrong"}
        ).status_code == 401

        login = client.post(
            "/api/auth/login",
            json={"username": "worker", "password": "worker1234"},
        )
        assert login.status_code == 200
        assert login.json()["role"] == "WORKER"
        assert "HttpOnly" in login.headers["set-cookie"]
        assert client.get("/api/auth/me").json()["username"] == "worker"
        assert len(client.get("/api/master-data/products").json()) == 2
        assert len(client.get("/api/master-data/locations").json()) == 5

        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/auth/me").status_code == 401

        admin_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin1234"},
        )
        assert admin_login.status_code == 200
        assert admin_login.json()["role"] == "ADMIN"


def test_admin_role_dependency_rejects_worker() -> None:
    worker = AuthenticatedUser(1, "worker", "倉管人員", "WORKER")
    admin = AuthenticatedUser(2, "admin", "管理者", "ADMIN")
    dependency = require_admin
    with pytest.raises(Exception) as error:
        dependency(user=worker)
    assert getattr(error.value, "status_code", None) == 403
    assert dependency(user=admin) == admin


def test_a3_seed_stock_is_complete_and_preserves_operated_balance(
    seeded_database: Path,
) -> None:
    connection = sqlite3.connect(seeded_database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT lots.lot_code, products.name, locations.code, stock_balances.qty
        FROM stock_balances
        JOIN lots ON lots.id = stock_balances.lot_id
        JOIN products ON products.id = lots.product_id
        JOIN locations ON locations.id = stock_balances.location_id
        ORDER BY lots.lot_code
        """
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        ("LOT-20260924-901", "紅蘿蔔", "B-03", 5),
        ("LOT-20260924-902", "青花菜", "B-04", 3),
    ]
    assert connection.execute(
        "SELECT count(*) FROM stock_movements WHERE kind = 'RECEIPT'"
    ).fetchone()[0] == 2
    carrot_lot_id = connection.execute(
        "SELECT id FROM lots WHERE lot_code = 'LOT-20260924-901'"
    ).fetchone()[0]
    carrot_location_id = connection.execute(
        "SELECT id FROM locations WHERE code = 'B-03'"
    ).fetchone()[0]
    connection.execute(
        "UPDATE stock_balances SET qty = 4 WHERE lot_id = ? AND location_id = ?",
        (carrot_lot_id, carrot_location_id),
    )
    connection.commit()
    connection.close()

    seed_database(seeded_database)

    connection = sqlite3.connect(seeded_database)
    assert connection.execute(
        "SELECT qty FROM stock_balances WHERE lot_id = ? AND location_id = ?",
        (carrot_lot_id, carrot_location_id),
    ).fetchone()[0] == 4
    assert connection.execute("SELECT count(*) FROM lots").fetchone()[0] == 2
    assert connection.execute("SELECT count(*) FROM stock_movements").fetchone()[0] == 2
    connection.close()


def test_stock_transaction_rolls_back_and_rejects_negative_balance(
    seeded_database: Path,
) -> None:
    with sqlite3.connect(seeded_database) as lookup:
        lot_id = lookup.execute(
            "SELECT id FROM lots WHERE lot_code = 'LOT-20260924-901'"
        ).fetchone()[0]
        location_id = lookup.execute(
            "SELECT id FROM locations WHERE code = 'B-03'"
        ).fetchone()[0]

    with pytest.raises(RuntimeError):
        with stock_transaction(seeded_database) as connection:
            assert change_balance(connection, lot_id, location_id, -2) == 3
            raise RuntimeError("force rollback")
    with stock_transaction(seeded_database) as connection:
        assert get_balance(connection, lot_id, location_id) == 5
        with pytest.raises(StockError, match="不可為負數"):
            change_balance(connection, lot_id, location_id, -6)
    with sqlite3.connect(seeded_database) as connection:
        assert connection.execute(
            "SELECT qty FROM stock_balances WHERE lot_id = ? AND location_id = ?",
            (lot_id, location_id),
        ).fetchone()[0] == 5


def test_pending_balance_blocks_source_and_existing_target(
    seeded_database: Path,
) -> None:
    with stock_transaction(seeded_database) as connection:
        lot_id = connection.execute(
            "SELECT id FROM lots WHERE lot_code = 'LOT-20260924-901'"
        ).fetchone()[0]
        source_id = connection.execute(
            "SELECT id FROM locations WHERE code = 'B-03'"
        ).fetchone()[0]
        target_id = connection.execute(
            "SELECT id FROM locations WHERE code = 'B-02'"
        ).fetchone()[0]
        worker_id = connection.execute(
            "SELECT id FROM users WHERE username = 'worker'"
        ).fetchone()[0]
        change_balance(connection, lot_id, target_id, 0, create_if_missing=True)
        connection.execute(
            """
            INSERT INTO adjustment_requests (
                kind, lot_id, location_id, original_qty, observed_qty,
                reason, requested_by
            ) VALUES ('COUNT', ?, ?, 5, 5, '測試來源凍結', ?)
            """,
            (lot_id, source_id, worker_id),
        )
        with pytest.raises(StockError, match="待審"):
            ensure_no_pending(connection, lot_id, source_id)
        connection.execute(
            "UPDATE adjustment_requests SET status = 'REJECTED' WHERE lot_id = ? AND location_id = ?",
            (lot_id, source_id),
        )
        connection.execute(
            """
            INSERT INTO adjustment_requests (
                kind, lot_id, location_id, original_qty, observed_qty,
                reason, requested_by
            ) VALUES ('COUNT', ?, ?, 0, 0, '測試目標凍結', ?)
            """,
            (lot_id, target_id, worker_id),
        )
        with pytest.raises(StockError, match="待審"):
            ensure_no_pending(connection, lot_id, target_id)


def test_stock_option_api_returns_seed_scenarios(seeded_database: Path) -> None:
    with TestClient(app) as client:
        assert client.get("/api/stock-options/lots").status_code == 401
        client.post(
            "/api/auth/login",
            json={"username": "worker", "password": "worker1234"},
        )
        lots = client.get("/api/stock-options/lots")
        balances = client.get("/api/stock-options/balances")
        locations = client.get("/api/stock-options/locations")
        assert lots.status_code == balances.status_code == locations.status_code == 200
        assert [(row["product_name"], row["total_qty"]) for row in lots.json()] == [
            ("紅蘿蔔", 5),
            ("青花菜", 3),
        ]
        assert [(row["location_code"], row["qty"]) for row in balances.json()] == [
            ("B-03", 5),
            ("B-04", 3),
        ]
        assert len(locations.json()) == 5


def test_a2_admin_can_create_and_edit_master_data_worker_cannot(
    seeded_database: Path,
) -> None:
    with TestClient(app) as client:
        client.post(
            "/api/auth/login",
            json={"username": "worker", "password": "worker1234"},
        )
        product_payload = {
            "name": "甘藍菜",
            "unit": "籠",
            "min_qty": 9,
            "target_qty": 15,
            "is_active": True,
        }
        assert client.post(
            "/api/master-data/products", json=product_payload
        ).status_code == 403
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin1234"},
        )

        created = client.post("/api/master-data/products", json=product_payload)
        assert created.status_code == 201
        product_id = created.json()["id"]
        product_payload["target_qty"] = 16
        updated = client.put(
            f"/api/master-data/products/{product_id}", json=product_payload
        )
        assert updated.status_code == 200
        assert updated.json()["target_qty"] == 16
        assert any(
            item["name"] == "甘藍菜" and item["target_qty"] == 16
            for item in client.get("/api/master-data/products").json()
        )

        warehouse_id = client.get("/api/master-data/warehouses").json()[0]["id"]
        location_payload = {
            "warehouse_id": warehouse_id,
            "code": "a-03",
            "is_active": True,
        }
        location = client.post("/api/master-data/locations", json=location_payload)
        assert location.status_code == 201
        assert location.json()["code"] == "A-03"
        location_payload.update({"code": "A-03", "is_active": False})
        disabled = client.put(
            f"/api/master-data/locations/{location.json()['id']}",
            json=location_payload,
        )
        assert disabled.status_code == 200
        assert disabled.json()["is_active"] is False


def test_a2_rejects_invalid_changes_without_writing(seeded_database: Path) -> None:
    with TestClient(app) as client:
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin1234"},
        )
        products = client.get("/api/master-data/products").json()
        carrot = next(item for item in products if item["name"] == "紅蘿蔔")
        changed_unit = {**carrot, "unit": "箱"}
        response = client.put(
            f"/api/master-data/products/{carrot['id']}", json=changed_unit
        )
        assert response.status_code == 409
        assert "不能修改單位" in response.json()["detail"]

        invalid = client.post(
            "/api/master-data/products",
            json={
                "name": "錯誤品項",
                "unit": "籠",
                "min_qty": 10,
                "target_qty": 5,
                "is_active": True,
            },
        )
        assert invalid.status_code == 422
        assert not any(
            item["name"] == "錯誤品項"
            for item in client.get("/api/master-data/products").json()
        )

        b03 = next(
            item
            for item in client.get("/api/master-data/locations").json()
            if item["code"] == "B-03"
        )
        disable = client.put(
            f"/api/master-data/locations/{b03['id']}",
            json={
                "warehouse_id": b03["warehouse_id"],
                "code": b03["code"],
                "is_active": False,
            },
        )
        assert disable.status_code == 409
        assert "仍有庫存" in disable.json()["detail"]
        refreshed = client.get("/api/master-data/locations").json()
        assert next(item for item in refreshed if item["code"] == "B-03")[
            "is_active"
        ] is True
