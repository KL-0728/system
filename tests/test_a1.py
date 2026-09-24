from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

import backend.database as database
from backend.auth import _sessions, require_admin
from backend.main import app
from backend.seed import seed_database
from backend.services.auth_service import AuthenticatedUser


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
