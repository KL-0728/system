from backend.database import connect_database
from backend.schemas.adjustment import AdjustmentCreate, AdjustmentRecord
from backend.services.stock_service import (
    StockError,
    ensure_no_pending,
    require_active_location,
    require_balance,
    stock_transaction,
)


_RECORD_SQL = """
    SELECT requests.id, requests.kind, requests.lot_id, lots.lot_code,
           products.name AS product_name, products.unit,
           requests.location_id, locations.code AS location_code,
           requests.original_qty, requests.observed_qty, requests.damaged_qty,
           requests.reason, requests.status,
           strftime('%Y-%m-%dT%H:%M:%SZ', requests.created_at) AS created_at
    FROM adjustment_requests AS requests
    JOIN lots ON lots.id = requests.lot_id
    JOIN products ON products.id = lots.product_id
    JOIN locations ON locations.id = requests.location_id
"""


def create_adjustment(payload: AdjustmentCreate, actor_id: int) -> AdjustmentRecord:
    with stock_transaction() as connection:
        require_active_location(connection, payload.location_id)
        original_qty = require_balance(connection, payload.lot_id, payload.location_id)
        ensure_no_pending(connection, payload.lot_id, payload.location_id)
        if payload.kind == "SCRAP" and payload.damaged_qty > original_qty:
            raise StockError("報廢量不可超過此批次與儲位的目前餘量")
        cursor = connection.execute(
            """INSERT INTO adjustment_requests
               (kind, lot_id, location_id, original_qty, observed_qty,
                damaged_qty, reason, requested_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (payload.kind, payload.lot_id, payload.location_id, original_qty,
             payload.observed_qty, payload.damaged_qty, payload.reason, actor_id),
        )
        row = connection.execute(
            _RECORD_SQL + " WHERE requests.id = ?", (cursor.lastrowid,)
        ).fetchone()
        result = AdjustmentRecord(**dict(row))
    return result


def list_my_adjustments(actor_id: int) -> list[AdjustmentRecord]:
    with connect_database() as connection:
        rows = connection.execute(
            _RECORD_SQL + " WHERE requests.requested_by = ? ORDER BY requests.id DESC LIMIT 100",
            (actor_id,),
        ).fetchall()
    return [AdjustmentRecord(**dict(row)) for row in rows]
