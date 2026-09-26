"""Add optional-feature storage without deleting or rewriting existing stock data."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from backend.database import connect_database


def migrate_extras(path: Path | None = None) -> None:
    with connect_database(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            names = {row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )}
            if not {"lots", "products", "users", "stock_balances"}.issubset(names):
                raise RuntimeError("資料庫尚未初始化，拒絕加做資料遷移")
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(lots)")}
            if "expires_on" not in columns:
                connection.execute("ALTER TABLE lots ADD COLUMN expires_on TEXT")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS shortage_demands (
                  id INTEGER PRIMARY KEY,
                  product_id INTEGER NOT NULL REFERENCES products(id),
                  qty INTEGER NOT NULL CHECK (typeof(qty) = 'integer' AND qty > 0),
                  note TEXT NOT NULL DEFAULT '',
                  actor_id INTEGER NOT NULL REFERENCES users(id),
                  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_shortage_demands_product_time
                ON shortage_demands(product_id, created_at)
            """)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


def backup_and_migrate(path: Path) -> Path:
    """Create an online-consistent SQLite backup before changing a real database."""
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_dir / f"{path.stem}-before-extras-{stamp}.db"
    if backup.exists():
        raise FileExistsError(f"備份檔已存在：{backup}")
    with connect_database(path) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    migrate_extras(path)
    return backup


if __name__ == "__main__":
    from backend.database import DATABASE_PATH

    backup_path = backup_and_migrate(DATABASE_PATH)
    print(f"加做資料遷移完成，原資料備份：{backup_path}")
