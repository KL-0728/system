from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import get_current_user, require_worker
from backend.database import connect_database
from backend.schemas.outbound import OutboundCreate, OutboundRecord, OutboundResult
from backend.schemas.transfer import TransferCreate, TransferRecord, TransferResult
from backend.services.auth_service import AuthenticatedUser
from backend.services.outbound_service import create_outbound
from backend.services.stock_service import StockError
from backend.services.transfer_service import create_transfer

router = APIRouter(prefix="/api/outbound", tags=["outbound"])


@router.post("", response_model=OutboundResult, status_code=201)
def outbound(payload: OutboundCreate, user: AuthenticatedUser = Depends(require_worker)) -> OutboundResult:
    try:
        return create_outbound(payload, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[OutboundRecord])
def records(
    lot_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    location_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[OutboundRecord]:
    # C1-only receipt lookup for uncertain submissions; B2 owns full history.
    conditions = ["m.kind = 'OUTBOUND'"]
    parameters: list[int] = []
    if lot_id is not None:
        conditions.append("m.lot_id = ?")
        parameters.append(lot_id)
    if location_id is not None:
        conditions.append("m.from_location_id = ?")
        parameters.append(location_id)
    with connect_database() as connection:
        rows = connection.execute(
            f"""SELECT m.id AS movement_id, m.lot_id, lots.lot_code,
                       products.name AS product_name, products.unit,
                       m.from_location_id AS location_id, locations.code AS location_code,
                       m.qty, users.display_name AS actor_name, m.note,
                       strftime('%Y-%m-%dT%H:%M:%SZ', m.created_at) AS created_at
                FROM stock_movements m
                JOIN lots ON lots.id = m.lot_id
                JOIN products ON products.id = lots.product_id
                JOIN locations ON locations.id = m.from_location_id
                JOIN users ON users.id = m.actor_id
                WHERE {' AND '.join(conditions)} ORDER BY m.id DESC LIMIT 100""",
            parameters,
        ).fetchall()
    return [OutboundRecord(**dict(row)) for row in rows]


@router.post("/transfers", response_model=TransferResult, status_code=201)
def transfer(payload: TransferCreate, user: AuthenticatedUser = Depends(require_worker)) -> TransferResult:
    try:
        return create_transfer(payload, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/transfers", response_model=list[TransferRecord])
def transfer_records(
    lot_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[TransferRecord]:
    # Only transfer receipts for C2 result verification; full history belongs to B2.
    condition = " AND m.lot_id = ?" if lot_id is not None else ""
    with connect_database() as connection:
        rows = connection.execute(
            f"""SELECT m.id AS movement_id, m.lot_id, lots.lot_code,
                       products.name AS product_name, products.unit,
                       m.from_location_id, source.code AS from_location_code,
                       m.to_location_id, target.code AS to_location_code, m.qty,
                       users.display_name AS actor_name,
                       strftime('%Y-%m-%dT%H:%M:%SZ', m.created_at) AS created_at
                FROM stock_movements m
                JOIN lots ON lots.id = m.lot_id
                JOIN products ON products.id = lots.product_id
                JOIN locations source ON source.id = m.from_location_id
                JOIN locations target ON target.id = m.to_location_id
                JOIN users ON users.id = m.actor_id
                WHERE m.kind = 'TRANSFER'{condition} ORDER BY m.id DESC LIMIT 100""",
            (lot_id,) if lot_id is not None else (),
        ).fetchall()
    return [TransferRecord(**dict(row)) for row in rows]
