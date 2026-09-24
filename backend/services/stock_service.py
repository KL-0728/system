from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from backend.database import connect_database


class StockError(ValueError):
    """A stock rule was rejected before any transaction was committed."""


@contextmanager
def stock_transaction(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Own one stock write transaction; nested use is not supported."""
    with connect_database(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


def get_balance(connection: sqlite3.Connection, lot_id: int, location_id: int) -> int | None:
    row = connection.execute(
        "SELECT qty FROM stock_balances WHERE lot_id = ? AND location_id = ?",
        (lot_id, location_id),
    ).fetchone()
    return None if row is None else int(row["qty"])


def require_balance(
    connection: sqlite3.Connection,
    lot_id: int,
    location_id: int,
    *,
    at_least: int = 0,
) -> int:
    if not isinstance(at_least, int) or isinstance(at_least, bool) or at_least < 0:
        raise StockError("需求數量必須是非負整數")
    balance = get_balance(connection, lot_id, location_id)
    if balance is None:
        raise StockError("找不到指定批次與儲位的庫存")
    if balance < at_least:
        raise StockError("庫存不足")
    return balance


def ensure_no_pending(
    connection: sqlite3.Connection, lot_id: int, location_id: int
) -> None:
    pending = connection.execute(
        """
        SELECT 1 FROM adjustment_requests
        WHERE lot_id = ? AND location_id = ? AND status = 'PENDING'
        """,
        (lot_id, location_id),
    ).fetchone()
    if pending is not None:
        raise StockError("此批次與儲位有待審申請，暫停庫存異動")


def require_active_location(connection: sqlite3.Connection, location_id: int) -> None:
    row = connection.execute(
        "SELECT is_active FROM locations WHERE id = ?", (location_id,)
    ).fetchone()
    if row is None:
        raise StockError("找不到指定儲位")
    if not row["is_active"]:
        raise StockError("指定儲位已停用")


def change_balance(
    connection: sqlite3.Connection,
    lot_id: int,
    location_id: int,
    delta: int,
    *,
    create_if_missing: bool = False,
) -> int:
    if not isinstance(delta, int) or isinstance(delta, bool):
        raise StockError("庫存異動量必須是整數")
    current = get_balance(connection, lot_id, location_id)
    if current is None:
        if not create_if_missing or delta < 0:
            raise StockError("找不到指定批次與儲位的庫存")
        connection.execute(
            "INSERT INTO stock_balances (lot_id, location_id, qty) VALUES (?, ?, ?)",
            (lot_id, location_id, delta),
        )
        return delta
    new_qty = current + delta
    if new_qty < 0:
        raise StockError("庫存不足，餘量不可為負數")
    connection.execute(
        "UPDATE stock_balances SET qty = ? WHERE lot_id = ? AND location_id = ?",
        (new_qty, lot_id, location_id),
    )
    return new_qty


def record_movement(
    connection: sqlite3.Connection,
    *,
    kind: str,
    lot_id: int,
    qty: int,
    actor_id: int,
    from_location_id: int | None = None,
    to_location_id: int | None = None,
    adjustment_request_id: int | None = None,
    note: str = "",
) -> int:
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        raise StockError("異動數量必須是正整數")
    cursor = connection.execute(
        """
        INSERT INTO stock_movements (
            kind, lot_id, from_location_id, to_location_id, qty,
            actor_id, adjustment_request_id, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            kind,
            lot_id,
            from_location_id,
            to_location_id,
            qty,
            actor_id,
            adjustment_request_id,
            note.strip(),
        ),
    )
    return int(cursor.lastrowid)
