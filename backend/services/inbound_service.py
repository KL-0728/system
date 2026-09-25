import sqlite3

from backend.schemas.inbound import InboundCreate, InboundResult
from backend.services.stock_service import (
    StockError,
    change_balance,
    record_movement,
    require_active_location,
    stock_transaction,
)


def require_active_product(connection: sqlite3.Connection, product_id: int) -> None:
    row = connection.execute(
        "SELECT is_active FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        raise StockError("找不到指定品項")
    if not row["is_active"]:
        raise StockError("指定品項已停用")


def next_lot_code(connection: sqlite3.Connection, received_date: str) -> str:
    """Return LOT-YYYYMMDD-NNN, one above the highest number used on that date."""
    prefix = f"LOT-{received_date.replace('-', '')}-"
    codes = connection.execute(
        "SELECT lot_code FROM lots WHERE lot_code LIKE ?", (prefix + "%",)
    ).fetchall()
    numbers = [
        int(suffix)
        for suffix in (row["lot_code"][len(prefix):] for row in codes)
        if suffix.isdigit()
    ]
    return f"{prefix}{max(numbers, default=0) + 1:03d}"


def create_inbound(payload: InboundCreate, actor_id: int) -> InboundResult:
    note = payload.note.strip()
    # One transaction: validate -> lot -> balance -> RECEIPT; any failure rolls back all.
    with stock_transaction() as connection:
        require_active_product(connection, payload.product_id)
        require_active_location(connection, payload.location_id)
        lot_code = next_lot_code(connection, payload.received_date)
        cursor = connection.execute(
            """
            INSERT INTO lots (lot_code, product_id, received_date, note, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lot_code, payload.product_id, payload.received_date, note, actor_id),
        )
        lot_id = int(cursor.lastrowid)
        qty = change_balance(
            connection, lot_id, payload.location_id, payload.qty, create_if_missing=True
        )
        movement_id = record_movement(
            connection, kind="RECEIPT", lot_id=lot_id, to_location_id=payload.location_id,
            qty=payload.qty, actor_id=actor_id, note=note,
        )
        result = InboundResult(
            lot_id=lot_id, lot_code=lot_code, product_id=payload.product_id,
            location_id=payload.location_id, received_date=payload.received_date,
            qty=qty, movement_id=movement_id,
        )
    return result
