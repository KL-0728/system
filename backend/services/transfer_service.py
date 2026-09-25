from backend.schemas.transfer import TransferCreate, TransferResult
from backend.services.stock_service import (
    StockError,
    change_balance,
    ensure_no_pending,
    get_balance,
    record_movement,
    require_active_location,
    require_balance,
    stock_transaction,
)


def create_transfer(payload: TransferCreate, actor_id: int) -> TransferResult:
    with stock_transaction() as connection:
        if payload.from_location_id == payload.to_location_id:
            raise StockError("來源與目標儲位不可相同")
        require_active_location(connection, payload.to_location_id)
        ensure_no_pending(connection, payload.lot_id, payload.from_location_id)
        ensure_no_pending(connection, payload.lot_id, payload.to_location_id)
        require_balance(connection, payload.lot_id, payload.from_location_id, at_least=payload.qty)
        target_qty = get_balance(connection, payload.lot_id, payload.to_location_id) or 0
        if target_qty + payload.qty > 9223372036854775807:
            raise StockError("目標餘量超過可儲存的整數範圍")
        from_qty = change_balance(connection, payload.lot_id, payload.from_location_id, -payload.qty)
        to_qty = change_balance(
            connection, payload.lot_id, payload.to_location_id, payload.qty, create_if_missing=True,
        )
        movement_id = record_movement(
            connection, kind="TRANSFER", lot_id=payload.lot_id, qty=payload.qty,
            from_location_id=payload.from_location_id, to_location_id=payload.to_location_id,
            actor_id=actor_id,
        )
        result = TransferResult(
            lot_id=payload.lot_id, from_location_id=payload.from_location_id,
            to_location_id=payload.to_location_id, from_qty=from_qty, to_qty=to_qty,
            movement_id=movement_id,
        )
    return result
