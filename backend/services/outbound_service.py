from backend.schemas.outbound import OutboundCreate, OutboundResult
from backend.services.stock_service import (
    change_balance,
    ensure_no_pending,
    record_movement,
    require_balance,
    stock_transaction,
)


def create_outbound(payload: OutboundCreate, actor_id: int) -> OutboundResult:
    with stock_transaction() as connection:
        ensure_no_pending(connection, payload.lot_id, payload.location_id)
        require_balance(connection, payload.lot_id, payload.location_id, at_least=payload.qty)
        remaining = change_balance(connection, payload.lot_id, payload.location_id, -payload.qty)
        movement_id = record_movement(
            connection, kind="OUTBOUND", lot_id=payload.lot_id,
            from_location_id=payload.location_id, qty=payload.qty,
            actor_id=actor_id, note=payload.note,
        )
        result = OutboundResult(
            lot_id=payload.lot_id, location_id=payload.location_id,
            qty=remaining, movement_id=movement_id,
        )
    return result
