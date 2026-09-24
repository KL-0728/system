from pathlib import Path
import sqlite3

from backend.database import DATABASE_PATH, connect_database
from backend.services.auth_service import hash_password


DEMO_USERS = (
    ("admin", "admin1234", "管理者", "ADMIN"),
    ("worker", "worker1234", "倉管人員", "WORKER"),
)
WAREHOUSES = (("A", "A 冷凍庫"), ("B", "B 冷凍庫"))
LOCATIONS = (("A", "A-01"), ("A", "A-02"), ("B", "B-02"), ("B", "B-03"), ("B", "B-04"))
PRODUCTS = (
    ("紅蘿蔔", "籠", 2, 8),
    ("青花菜", "籠", 2, 6),
)


def seed_database(path: Path = DATABASE_PATH) -> None:
    with connect_database(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            for username, password, display_name, role in DEMO_USERS:
                exists = connection.execute(
                    "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)
                ).fetchone()
                if exists is None:
                    connection.execute(
                        "INSERT INTO users (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
                        (username, hash_password(password), display_name, role),
                    )
            for code, name in WAREHOUSES:
                connection.execute(
                    """
                    INSERT INTO warehouses (code, name)
                    SELECT ?, ? WHERE NOT EXISTS (
                        SELECT 1 FROM warehouses WHERE code = ?
                    )
                    """,
                    (code, name, code),
                )
            warehouse_ids = {
                row["code"]: row["id"]
                for row in connection.execute("SELECT id, code FROM warehouses")
            }
            for warehouse_code, location_code in LOCATIONS:
                connection.execute(
                    """
                    INSERT INTO locations (warehouse_id, code)
                    SELECT ?, ? WHERE NOT EXISTS (
                        SELECT 1 FROM locations WHERE code = ?
                    )
                    """,
                    (warehouse_ids[warehouse_code], location_code, location_code),
                )
            for name, unit, min_qty, target_qty in PRODUCTS:
                connection.execute(
                    """
                    INSERT INTO products (name, unit, min_qty, target_qty)
                    SELECT ?, ?, ?, ? WHERE NOT EXISTS (
                        SELECT 1 FROM products WHERE name = ? COLLATE NOCASE
                    )
                    """,
                    (name, unit, min_qty, target_qty, name),
                )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


if __name__ == "__main__":
    try:
        seed_database()
    except sqlite3.OperationalError as error:
        raise SystemExit(f"Seed failed: {error}") from error
    print("Seed complete; existing records were preserved.")
