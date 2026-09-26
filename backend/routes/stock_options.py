from fastapi import APIRouter, Depends, Query

from backend.auth import get_current_user
from backend.database import connect_database
from backend.schemas.stock_options import BalanceOption, LotOption, StockLocationOption
from backend.services.auth_service import AuthenticatedUser


router = APIRouter(prefix="/api/stock-options", tags=["stock-options"])


@router.get("/lots", response_model=list[LotOption])
def list_lot_options(
    product_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[LotOption]:
    sql = """
        SELECT lots.id AS lot_id, lots.lot_code, products.id AS product_id,
               products.name AS product_name, products.unit, lots.received_date,
               COALESCE(SUM(stock_balances.qty), 0) AS total_qty
        FROM lots
        JOIN products ON products.id = lots.product_id
        LEFT JOIN stock_balances ON stock_balances.lot_id = lots.id
    """
    parameters: tuple[int, ...] = ()
    if product_id is not None:
        sql += " WHERE products.id = ?"
        parameters = (product_id,)
    sql += " GROUP BY lots.id ORDER BY lots.received_date, lots.lot_code"
    with connect_database() as connection:
        rows = connection.execute(sql, parameters).fetchall()
    return [LotOption(**dict(row)) for row in rows]


@router.get("/balances", response_model=list[BalanceOption])
def list_balance_options(
    lot_id: int | None = Query(default=None, gt=0, le=9223372036854775807),
    positive_only: bool = True,
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[BalanceOption]:
    conditions: list[str] = []
    parameters: list[int] = []
    if lot_id is not None:
        conditions.append("lots.id = ?")
        parameters.append(lot_id)
    if positive_only:
        conditions.append("stock_balances.qty > 0")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with connect_database() as connection:
        rows = connection.execute(
            f"""
            SELECT lots.id AS lot_id, lots.lot_code, products.id AS product_id,
                   products.name AS product_name, products.unit, lots.received_date,
                   locations.id AS location_id, locations.code AS location_code,
                   warehouses.code AS warehouse_code, stock_balances.qty,
                   EXISTS (
                       SELECT 1 FROM adjustment_requests AS requests
                       WHERE requests.lot_id = stock_balances.lot_id
                         AND requests.location_id = stock_balances.location_id
                         AND requests.status = 'PENDING'
                   ) AS has_pending
            FROM stock_balances
            JOIN lots ON lots.id = stock_balances.lot_id
            JOIN products ON products.id = lots.product_id
            JOIN locations ON locations.id = stock_balances.location_id
            JOIN warehouses ON warehouses.id = locations.warehouse_id
            {where}
            ORDER BY products.name COLLATE NOCASE, lots.received_date,
                     lots.lot_code, locations.code
            """,
            parameters,
        ).fetchall()
    return [
        BalanceOption(**{**dict(row), "has_pending": bool(row["has_pending"])})
        for row in rows
    ]


@router.get("/locations", response_model=list[StockLocationOption])
def list_active_location_options(
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[StockLocationOption]:
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT locations.id AS location_id, locations.code AS location_code,
                   warehouses.code AS warehouse_code,
                   warehouses.name AS warehouse_name
            FROM locations
            JOIN warehouses ON warehouses.id = locations.warehouse_id
            WHERE locations.is_active = 1
            ORDER BY warehouses.code, locations.code
            """
        ).fetchall()
    return [StockLocationOption(**dict(row)) for row in rows]
