from datetime import date

from backend.database import connect_database
from backend.schemas.inbound import taiwan_today
from backend.schemas.inventory import InventoryBalance, InventoryMovement


def search_inventory(
    product_id: int | None = None,
    lot_code: str | None = None,
    location_id: int | None = None,
) -> list[InventoryBalance]:
    conditions: list[str] = []
    parameters: list[int | str] = []
    if product_id is not None:
        conditions.append("lots.product_id = ?")
        parameters.append(product_id)
    if lot_code:
        conditions.append("instr(lower(lots.lot_code), lower(?)) > 0")
        parameters.append(lot_code.strip())
    if location_id is not None:
        conditions.append("balances.location_id = ?")
        parameters.append(location_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with connect_database() as connection:
        rows = connection.execute(
            f"""
            WITH totals AS (
                SELECT lot_id, SUM(qty) AS total_qty
                FROM stock_balances GROUP BY lot_id
            )
            SELECT lots.id AS lot_id, lots.lot_code, products.id AS product_id,
                   products.name AS product_name, products.unit, lots.received_date,
                   lots.expires_on,
                   receiver.display_name AS received_by,
                   locations.id AS location_id, locations.code AS location_code,
                   warehouses.code AS warehouse_code, warehouses.name AS warehouse_name,
                   balances.qty, totals.total_qty
            FROM lots
            JOIN products ON products.id = lots.product_id
            JOIN users AS receiver ON receiver.id = lots.created_by
            JOIN stock_balances AS balances ON balances.lot_id = lots.id
            JOIN totals ON totals.lot_id = lots.id
            JOIN locations ON locations.id = balances.location_id
            JOIN warehouses ON warehouses.id = locations.warehouse_id
            {where}
            ORDER BY lots.received_date, lots.lot_code, locations.code
            """,
            parameters,
        ).fetchall()
    today = taiwan_today()
    result: list[InventoryBalance] = []
    for row in rows:
        expires_on = row["expires_on"]
        days_to_expiry = (date.fromisoformat(expires_on) - today).days if expires_on else None
        status = "未提供" if days_to_expiry is None else (
            "已到期" if days_to_expiry < 0 else "即將到期" if days_to_expiry <= 7 else "未到期"
        )
        result.append(InventoryBalance(
            **dict(row), expiry_status=status,
            age_days=max((today - date.fromisoformat(row["received_date"])).days, 0),
        ))
    return result


def lot_movements(lot_id: int) -> list[InventoryMovement]:
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT movements.id AS movement_id, movements.lot_id, movements.kind,
                   source.code AS from_location_code, target.code AS to_location_code,
                   movements.qty, users.display_name AS actor_name, movements.note,
                   movements.adjustment_request_id,
                   strftime('%Y-%m-%dT%H:%M:%SZ', movements.created_at) AS created_at
            FROM stock_movements AS movements
            JOIN users ON users.id = movements.actor_id
            LEFT JOIN locations AS source ON source.id = movements.from_location_id
            LEFT JOIN locations AS target ON target.id = movements.to_location_id
            WHERE movements.lot_id = ?
            ORDER BY movements.created_at DESC, movements.id DESC
            """,
            (lot_id,),
        ).fetchall()
    return [InventoryMovement(**dict(row)) for row in rows]
