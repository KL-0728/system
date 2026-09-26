import sqlite3

from backend.schemas.master_data import LocationWrite, ProductWrite


class MasterDataError(ValueError):
    pass


class MasterDataNotFound(MasterDataError):
    pass


class MasterDataConflict(MasterDataError):
    pass


def create_product(connection: sqlite3.Connection, data: ProductWrite) -> int:
    try:
        cursor = connection.execute(
            """
            INSERT INTO products (name, unit, min_qty, target_qty, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (data.name, data.unit, data.min_qty, data.target_qty, int(data.is_active)),
        )
    except sqlite3.IntegrityError as error:
        raise MasterDataConflict("品項名稱已存在") from error
    return int(cursor.lastrowid)


def update_product(
    connection: sqlite3.Connection, product_id: int, data: ProductWrite
) -> None:
    current = connection.execute(
        "SELECT unit FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if current is None:
        raise MasterDataNotFound("找不到品項")
    if current["unit"] != data.unit:
        has_movement = connection.execute(
            """
            SELECT 1 FROM stock_movements
            JOIN lots ON lots.id = stock_movements.lot_id
            WHERE lots.product_id = ? LIMIT 1
            """,
            (product_id,),
        ).fetchone()
        if has_movement is not None:
            raise MasterDataConflict("已有庫存異動的品項不能修改單位")
        if connection.execute(
            "SELECT 1 FROM shortage_demands WHERE product_id = ? LIMIT 1", (product_id,)
        ).fetchone() is not None:
            raise MasterDataConflict("已有缺貨需求紀錄的品項不能修改單位")
    try:
        connection.execute(
            """
            UPDATE products
            SET name = ?, unit = ?, min_qty = ?, target_qty = ?, is_active = ?
            WHERE id = ?
            """,
            (
                data.name,
                data.unit,
                data.min_qty,
                data.target_qty,
                int(data.is_active),
                product_id,
            ),
        )
    except sqlite3.IntegrityError as error:
        raise MasterDataConflict("品項名稱已存在") from error


def create_location(connection: sqlite3.Connection, data: LocationWrite) -> int:
    _require_warehouse_code(connection, data.warehouse_id, data.code)
    try:
        cursor = connection.execute(
            "INSERT INTO locations (warehouse_id, code, is_active) VALUES (?, ?, ?)",
            (data.warehouse_id, data.code, int(data.is_active)),
        )
    except sqlite3.IntegrityError as error:
        raise MasterDataConflict("儲位代碼已存在") from error
    return int(cursor.lastrowid)


def update_location(
    connection: sqlite3.Connection, location_id: int, data: LocationWrite
) -> None:
    current = connection.execute(
        "SELECT is_active FROM locations WHERE id = ?", (location_id,)
    ).fetchone()
    if current is None:
        raise MasterDataNotFound("找不到儲位")
    _require_warehouse_code(connection, data.warehouse_id, data.code)
    if current["is_active"] and not data.is_active:
        quantity = connection.execute(
            "SELECT COALESCE(SUM(qty), 0) FROM stock_balances WHERE location_id = ?",
            (location_id,),
        ).fetchone()[0]
        if quantity > 0:
            raise MasterDataConflict("儲位仍有庫存，搬空後才能停用")
        if connection.execute(
            "SELECT 1 FROM adjustment_requests WHERE location_id = ? AND status = 'PENDING' LIMIT 1",
            (location_id,),
        ).fetchone() is not None:
            raise MasterDataConflict("儲位仍有待審申請，審核結束後才能停用")
    try:
        connection.execute(
            """
            UPDATE locations SET warehouse_id = ?, code = ?, is_active = ?
            WHERE id = ?
            """,
            (data.warehouse_id, data.code, int(data.is_active), location_id),
        )
    except sqlite3.IntegrityError as error:
        raise MasterDataConflict("儲位代碼已存在") from error


def _require_warehouse_code(connection: sqlite3.Connection, warehouse_id: int, code: str) -> None:
    warehouse = connection.execute(
        "SELECT code FROM warehouses WHERE id = ?", (warehouse_id,)
    ).fetchone()
    if warehouse is None:
        raise MasterDataNotFound("找不到冷凍庫")
    if not code.startswith(f"{warehouse['code']}-"):
        raise MasterDataConflict("儲位代碼必須符合所選冷凍庫")
