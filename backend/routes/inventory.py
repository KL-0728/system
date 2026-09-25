from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import get_current_user, require_worker
from backend.database import connect_database
from backend.schemas.inbound import InboundCreate, InboundRecord, InboundResult
from backend.schemas.inventory import InventoryBalance, InventoryMovement
from backend.services.auth_service import AuthenticatedUser
from backend.services.inbound_service import create_inbound
from backend.services.inventory_service import lot_movements, search_inventory
from backend.services.stock_service import StockError

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/stock", response_model=list[InventoryBalance])
def inventory_stock(
    product_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    lot_code: str | None = Query(default=None, max_length=100),
    location_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[InventoryBalance]:
    return search_inventory(product_id, lot_code, location_id)


@router.get("/movements", response_model=list[InventoryMovement])
def inventory_movements(
    lot_id: int = Query(gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[InventoryMovement]:
    return lot_movements(lot_id)


@router.post("/inbound", response_model=InboundResult, status_code=201)
def inbound(payload: InboundCreate, user: AuthenticatedUser = Depends(require_worker)) -> InboundResult:
    try:
        return create_inbound(payload, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/inbound", response_model=list[InboundRecord])
def inbound_records(
    lot_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[InboundRecord]:
    # B1 receipt lookup for checking uncertain submissions; B2 adds full search and history.
    condition = " AND m.lot_id = ?" if lot_id is not None else ""
    with connect_database() as connection:
        rows = connection.execute(
            f"""SELECT m.id AS movement_id, m.lot_id, lots.lot_code,
                       products.name AS product_name, products.unit, lots.received_date,
                       m.to_location_id AS location_id, locations.code AS location_code,
                       m.qty, users.display_name AS actor_name, m.note,
                       strftime('%Y-%m-%dT%H:%M:%SZ', m.created_at) AS created_at
                FROM stock_movements m
                JOIN lots ON lots.id = m.lot_id
                JOIN products ON products.id = lots.product_id
                JOIN locations ON locations.id = m.to_location_id
                JOIN users ON users.id = m.actor_id
                WHERE m.kind = 'RECEIPT'{condition} ORDER BY m.id DESC LIMIT 100""",
            (lot_id,) if lot_id is not None else (),
        ).fetchall()
    return [InboundRecord(**dict(row)) for row in rows]
