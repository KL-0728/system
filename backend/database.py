"""SQLite connections and explicit one-time empty database initialization."""
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT / "data" / "inventory.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@contextmanager
def connect_database(path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    # Do not silently create an empty database if initialization was missed.
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation refuses to overwrite any existing database.
    with DATABASE_PATH.open("xb"):
        pass
    try:
        with connect_database() as connection:
            connection.executescript(
                "BEGIN IMMEDIATE;\n" + SCHEMA_PATH.read_text(encoding="utf-8") + "\nCOMMIT;"
            )
    except BaseException:
        DATABASE_PATH.unlink()
        raise


if __name__ == "__main__":
    try:
        initialize_database()
    except FileExistsError:
        raise SystemExit("Database already exists; initialization refused. No data changed.")
    print(f"Initialized empty database: {DATABASE_PATH}")
