"""Add receiving timestamps and warehouse count sessions to an existing database.

Run only while the service is stopped. The command creates an SQLite backup first.
"""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from backend.database import connect_database


def migrate_maintenance(path: Path) -> None:
    with connect_database(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            names = {row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )}
            if not {"lots", "warehouses", "locations", "stock_balances", "adjustment_requests"}.issubset(names):
                raise RuntimeError("資料庫尚未初始化，拒絕維護資料遷移")
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(lots)")}
            if "received_at" not in columns:
                connection.execute("ALTER TABLE lots ADD COLUMN received_at TEXT")
            statements = """
                CREATE TABLE IF NOT EXISTS warehouse_counts (
                  id INTEGER PRIMARY KEY,
                  warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
                  created_by INTEGER NOT NULL REFERENCES users(id),
                  status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'COMPLETE', 'CANCELLED')),
                  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  completed_at TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_open_count_per_warehouse
                  ON warehouse_counts(warehouse_id) WHERE status = 'OPEN';
                CREATE TABLE IF NOT EXISTS warehouse_count_items (
                  id INTEGER PRIMARY KEY,
                  count_id INTEGER NOT NULL REFERENCES warehouse_counts(id),
                  location_id INTEGER NOT NULL REFERENCES locations(id),
                  lot_id INTEGER REFERENCES lots(id),
                  original_qty INTEGER NOT NULL CHECK (original_qty >= 0),
                  observed_qty INTEGER CHECK (observed_qty IS NULL OR observed_qty >= 0),
                  adjustment_request_id INTEGER UNIQUE REFERENCES adjustment_requests(id),
                  checked_at TEXT,
                  note TEXT NOT NULL DEFAULT '',
                  UNIQUE (count_id, location_id, lot_id)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_empty_count_item_per_location
                  ON warehouse_count_items(count_id, location_id) WHERE lot_id IS NULL;
            """
            for statement in statements.split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


def backup_and_migrate(path: Path) -> Path:
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_dir / f"{path.stem}-before-maintenance-{stamp}.db"
    with connect_database(path) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    migrate_maintenance(path)
    return backup


if __name__ == "__main__":
    from backend.database import DATABASE_PATH

    print(f"維護資料遷移完成，原資料備份：{backup_and_migrate(DATABASE_PATH)}")
