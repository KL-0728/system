from backend.database import connect_database
from backend.schemas.adjustment import (
    AdjustmentCreate, AdjustmentDetail, AdjustmentRecord,
    AdjustmentReview, AdjustmentReviewResult,
)
from backend.services.stock_service import (
    StockError,
    change_balance,
    ensure_no_pending,
    record_movement,
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
           strftime('%Y-%m-%dT%H:%M:%SZ', requests.created_at) AS created_at,
           reviewer.display_name AS reviewer_name, requests.review_note,
           strftime('%Y-%m-%dT%H:%M:%SZ', requests.reviewed_at) AS reviewed_at
    FROM adjustment_requests AS requests
    JOIN lots ON lots.id = requests.lot_id
    JOIN products ON products.id = lots.product_id
    JOIN locations ON locations.id = requests.location_id
    LEFT JOIN users AS reviewer ON reviewer.id = requests.reviewed_by
"""

_DETAIL_SQL = """
    SELECT requests.id, requests.kind, requests.lot_id, lots.lot_code,
           products.name AS product_name, products.unit,
           requests.location_id, locations.code AS location_code,
           requests.original_qty, requests.observed_qty, requests.damaged_qty,
           requests.reason, requests.status,
           strftime('%Y-%m-%dT%H:%M:%SZ', requests.created_at) AS created_at,
           requests.requested_by, requester.display_name AS requester_name,
           balances.qty AS current_qty,
           CASE WHEN requests.kind = 'COUNT'
                THEN requests.observed_qty - requests.original_qty
                ELSE -requests.damaged_qty END AS difference,
           requests.reviewed_by, reviewer.display_name AS reviewer_name,
           requests.review_note,
           strftime('%Y-%m-%dT%H:%M:%SZ', requests.reviewed_at) AS reviewed_at,
           movements.id AS movement_id
    FROM adjustment_requests AS requests
    JOIN lots ON lots.id = requests.lot_id
    JOIN products ON products.id = lots.product_id
    JOIN locations ON locations.id = requests.location_id
    JOIN users AS requester ON requester.id = requests.requested_by
    JOIN stock_balances AS balances
      ON balances.lot_id = requests.lot_id AND balances.location_id = requests.location_id
    LEFT JOIN users AS reviewer ON reviewer.id = requests.reviewed_by
    LEFT JOIN stock_movements AS movements ON movements.adjustment_request_id = requests.id
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


def list_pending_adjustments() -> list[AdjustmentDetail]:
    with connect_database() as connection:
        rows = connection.execute(
            _DETAIL_SQL + " WHERE requests.status = 'PENDING' ORDER BY requests.id ASC"
        ).fetchall()
    return [AdjustmentDetail(**dict(row)) for row in rows]


def list_reviewed_adjustments() -> list[AdjustmentDetail]:
    with connect_database() as connection:
        rows = connection.execute(
            _DETAIL_SQL + " WHERE requests.status != 'PENDING' ORDER BY requests.reviewed_at DESC, requests.id DESC LIMIT 100"
        ).fetchall()
    return [AdjustmentDetail(**dict(row)) for row in rows]


def get_adjustment_detail(request_id: int) -> AdjustmentDetail | None:
    with connect_database() as connection:
        row = connection.execute(
            _DETAIL_SQL + " WHERE requests.id = ?", (request_id,)
        ).fetchone()
    return None if row is None else AdjustmentDetail(**dict(row))


def review_adjustment(
    request_id: int, payload: AdjustmentReview, reviewer_id: int
) -> AdjustmentReviewResult:
    with stock_transaction() as connection:
        request = connection.execute(
            "SELECT * FROM adjustment_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if request is None:
            raise StockError("找不到指定申請")
        if request["status"] != "PENDING":
            raise StockError("此申請已審核，不能重複操作")
        if request["requested_by"] == reviewer_id:
            raise StockError("不能審核自己提交的申請")

        original_qty = int(request["original_qty"])
        new_qty = require_balance(connection, request["lot_id"], request["location_id"])
        delta = 0
        movement_id = None
        if payload.action == "APPROVE":
            if new_qty != original_qty:
                raise StockError("目前餘量與申請原數不一致，不能核准")
            if request["kind"] == "COUNT":
                delta = int(request["observed_qty"]) - original_qty
                movement_kind = "COUNT_GAIN" if delta > 0 else "COUNT_LOSS"
            else:
                damaged_qty = int(request["damaged_qty"])
                if damaged_qty > original_qty:
                    raise StockError("報廢量不可超過申請原數")
                delta = -damaged_qty
                movement_kind = "SCRAP"
            if delta:
                if delta > 0:
                    require_active_location(connection, request["location_id"])
                new_qty = change_balance(
                    connection, request["lot_id"], request["location_id"], delta
                )
                movement_id = record_movement(
                    connection,
                    kind=movement_kind,
                    lot_id=request["lot_id"],
                    qty=abs(delta),
                    actor_id=reviewer_id,
                    from_location_id=request["location_id"] if delta < 0 else None,
                    to_location_id=request["location_id"] if delta > 0 else None,
                    adjustment_request_id=request_id,
                    note=request["reason"],
                )
        status = "APPROVED" if payload.action == "APPROVE" else "REJECTED"
        updated = connection.execute(
            """UPDATE adjustment_requests
               SET status = ?, reviewed_by = ?, review_note = ?, reviewed_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status = 'PENDING'""",
            (status, reviewer_id, payload.review_note, request_id),
        )
        if updated.rowcount != 1:
            raise StockError("此申請已審核，不能重複操作")
        reviewed_at = connection.execute(
            "SELECT strftime('%Y-%m-%dT%H:%M:%SZ', reviewed_at) FROM adjustment_requests WHERE id = ?",
            (request_id,),
        ).fetchone()[0]
        result = AdjustmentReviewResult(
            request_id=request_id, status=status, original_qty=original_qty,
            new_qty=new_qty, delta=delta, movement_id=movement_id,
            reviewed_by=reviewer_id, review_note=payload.review_note,
            reviewed_at=reviewed_at,
        )
    return result
