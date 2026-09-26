from backend.database import connect_database
from backend.schemas.extras import ExpiryResult, ShortageDemandCreate, ShortageDemandRecord
from backend.services.stock_service import StockError, stock_transaction


def create_shortage_demand(payload: ShortageDemandCreate, actor_id: int) -> ShortageDemandRecord:
    with stock_transaction() as connection:
        product = connection.execute(
            "SELECT is_active FROM products WHERE id = ?", (payload.product_id,)
        ).fetchone()
        if product is None:
            raise LookupError("找不到指定品項")
        if not product["is_active"]:
            raise StockError("指定品項已停用")
        cursor = connection.execute(
            "INSERT INTO shortage_demands (product_id, qty, note, actor_id) VALUES (?, ?, ?, ?)",
            (payload.product_id, payload.qty, payload.note.strip(), actor_id),
        )
        row = connection.execute("""
            SELECT demands.id, demands.product_id, products.name AS product_name,
                   products.unit, demands.qty, demands.note,
                   users.display_name AS actor_name,
                   strftime('%Y-%m-%dT%H:%M:%SZ', demands.created_at) AS created_at
            FROM shortage_demands AS demands
            JOIN products ON products.id = demands.product_id
            JOIN users ON users.id = demands.actor_id
            WHERE demands.id = ?
        """, (cursor.lastrowid,)).fetchone()
        result = ShortageDemandRecord(**dict(row))
    return result


def list_shortage_demands(actor_id: int | None = None) -> list[ShortageDemandRecord]:
    condition = "WHERE demands.actor_id = ?" if actor_id is not None else ""
    with connect_database() as connection:
        rows = connection.execute(f"""
            SELECT demands.id, demands.product_id, products.name AS product_name,
                   products.unit, demands.qty, demands.note,
                   users.display_name AS actor_name,
                   strftime('%Y-%m-%dT%H:%M:%SZ', demands.created_at) AS created_at
            FROM shortage_demands AS demands
            JOIN products ON products.id = demands.product_id
            JOIN users ON users.id = demands.actor_id
            {condition}
            ORDER BY demands.id DESC LIMIT 100
        """, (actor_id,) if actor_id is not None else ()).fetchall()
    return [ShortageDemandRecord(**dict(row)) for row in rows]


def set_lot_expiry(lot_id: int, expires_on: str | None) -> ExpiryResult:
    with stock_transaction() as connection:
        lot = connection.execute(
            "SELECT id, lot_code FROM lots WHERE id = ?", (lot_id,)
        ).fetchone()
        if lot is None:
            raise LookupError("找不到指定批次")
        connection.execute(
            "UPDATE lots SET expires_on = ? WHERE id = ?", (expires_on, lot_id)
        )
        result = ExpiryResult(lot_id=lot_id, lot_code=lot["lot_code"], expires_on=expires_on)
    return result
