"""Warehouse-wide count checklist; stock changes still use normal review requests."""
import sqlite3

from backend.database import connect_database
from backend.schemas.warehouse_count import CountSession
from backend.services.stock_service import StockError, ensure_no_pending, stock_transaction


def _session(connection: sqlite3.Connection, count_id: int) -> CountSession | None:
    header = connection.execute("""
        SELECT counts.id, counts.warehouse_id, warehouses.code AS warehouse_code,
               warehouses.name AS warehouse_name, counts.created_by, counts.status,
               strftime('%Y-%m-%dT%H:%M:%SZ', counts.started_at) AS started_at,
               strftime('%Y-%m-%dT%H:%M:%SZ', counts.completed_at) AS completed_at
        FROM warehouse_counts counts
        JOIN warehouses ON warehouses.id = counts.warehouse_id
        WHERE counts.id = ?
    """, (count_id,)).fetchone()
    if header is None:
        return None
    items = connection.execute("""
        SELECT items.id, items.location_id, locations.code AS location_code,
               items.lot_id, lots.lot_code, products.name AS product_name, products.unit,
               items.original_qty, items.observed_qty, items.adjustment_request_id,
               requests.status AS adjustment_status,
               strftime('%Y-%m-%dT%H:%M:%SZ', items.checked_at) AS checked_at,
               items.note
        FROM warehouse_count_items items
        JOIN locations ON locations.id = items.location_id
        LEFT JOIN lots ON lots.id = items.lot_id
        LEFT JOIN products ON products.id = lots.product_id
        LEFT JOIN adjustment_requests requests ON requests.id = items.adjustment_request_id
        WHERE items.count_id = ?
        ORDER BY locations.code, products.name, lots.received_date, lots.lot_code
    """, (count_id,)).fetchall()
    return CountSession(**dict(header), items=[dict(row) for row in items])


def list_counts() -> list[CountSession]:
    with connect_database() as connection:
        ids = [row["id"] for row in connection.execute(
            "SELECT id FROM warehouse_counts ORDER BY id DESC LIMIT 20"
        )]
        return [_session(connection, count_id) for count_id in ids]


def get_count(count_id: int) -> CountSession | None:
    with connect_database() as connection:
        return _session(connection, count_id)


def start_count(warehouse_id: int, actor_id: int) -> CountSession:
    with stock_transaction() as connection:
        warehouse = connection.execute("SELECT id FROM warehouses WHERE id = ?", (warehouse_id,)).fetchone()
        if warehouse is None:
            raise StockError("找不到指定倉庫")
        existing = connection.execute("""
            SELECT id FROM warehouse_counts WHERE warehouse_id = ? AND status = 'OPEN'
        """, (warehouse_id,)).fetchone()
        if existing:
            return _session(connection, existing["id"])
        locations = connection.execute("""
            SELECT id FROM locations WHERE warehouse_id = ? AND is_active = 1 ORDER BY code
        """, (warehouse_id,)).fetchall()
        if not locations:
            raise StockError("這座倉庫沒有啟用儲位")
        cursor = connection.execute(
            "INSERT INTO warehouse_counts (warehouse_id, created_by) VALUES (?, ?)",
            (warehouse_id, actor_id),
        )
        count_id = int(cursor.lastrowid)
        for location in locations:
            balances = connection.execute("""
                SELECT lot_id, qty FROM stock_balances
                WHERE location_id = ? AND qty > 0 ORDER BY lot_id
            """, (location["id"],)).fetchall()
            if not balances:
                connection.execute("""
                    INSERT INTO warehouse_count_items (count_id, location_id, original_qty)
                    VALUES (?, ?, 0)
                """, (count_id, location["id"]))
            for balance in balances:
                connection.execute("""
                    INSERT INTO warehouse_count_items
                    (count_id, location_id, lot_id, original_qty) VALUES (?, ?, ?, ?)
                """, (count_id, location["id"], balance["lot_id"], balance["qty"]))
        result = _session(connection, count_id)
    return result


def check_item(count_id: int, item_id: int, observed_qty: int, note: str, actor_id: int) -> CountSession:
    note = note.strip()
    with stock_transaction() as connection:
        session = connection.execute(
            "SELECT status FROM warehouse_counts WHERE id = ?", (count_id,)
        ).fetchone()
        if session is None or session["status"] != "OPEN":
            raise StockError("盤點不存在或已完成")
        item = connection.execute("""
            SELECT * FROM warehouse_count_items WHERE id = ? AND count_id = ?
        """, (item_id, count_id)).fetchone()
        if item is None:
            raise StockError("盤點項目不存在")
        if item["checked_at"] is not None:
            raise StockError("這一格已確認，請更新盤點紀錄")
        if item["lot_id"] is None:
            if observed_qty != 0:
                raise StockError("空儲位若發現未登錄貨物，請先通知管理者確認批次")
            changed = connection.execute("""
                SELECT 1 FROM stock_balances WHERE location_id = ? AND qty > 0 LIMIT 1
            """, (item["location_id"],)).fetchone()
            if changed:
                raise StockError("此儲位已有新庫存，請重新建立盤點")
        else:
            current = connection.execute("""
                SELECT qty FROM stock_balances WHERE lot_id = ? AND location_id = ?
            """, (item["lot_id"], item["location_id"])).fetchone()
            if current is None or current["qty"] != item["original_qty"]:
                raise StockError("帳面庫存已變更，請重新建立盤點")
            ensure_no_pending(connection, item["lot_id"], item["location_id"])
        request_id = None
        if observed_qty != item["original_qty"]:
            if not note:
                raise StockError("有盤差時必須填寫原因")
            cursor = connection.execute("""
                INSERT INTO adjustment_requests
                (kind, lot_id, location_id, original_qty, observed_qty, reason, requested_by)
                VALUES ('COUNT', ?, ?, ?, ?, ?, ?)
            """, (item["lot_id"], item["location_id"], item["original_qty"], observed_qty, note, actor_id))
            request_id = int(cursor.lastrowid)
        connection.execute("""
            UPDATE warehouse_count_items
            SET observed_qty = ?, adjustment_request_id = ?, checked_at = CURRENT_TIMESTAMP, note = ?
            WHERE id = ?
        """, (observed_qty, request_id, note, item_id))
        result = _session(connection, count_id)
    return result


def reopen_item(count_id: int, item_id: int) -> CountSession:
    with stock_transaction() as connection:
        session = connection.execute(
            "SELECT status FROM warehouse_counts WHERE id = ?", (count_id,)
        ).fetchone()
        if session is None or session["status"] != "OPEN":
            raise StockError("盤點不存在或已結束")
        updated = connection.execute("""
            UPDATE warehouse_count_items
            SET observed_qty = NULL, checked_at = NULL, note = ''
            WHERE id = ? AND count_id = ? AND checked_at IS NOT NULL
              AND adjustment_request_id IS NULL
        """, (item_id, count_id))
        if updated.rowcount != 1:
            raise StockError("這一格尚未確認，或已有盤差申請；盤差須由管理者審核後重新盤點")
        result = _session(connection, count_id)
    return result


def complete_count(count_id: int) -> CountSession:
    with stock_transaction() as connection:
        session = connection.execute(
            "SELECT status FROM warehouse_counts WHERE id = ?", (count_id,)
        ).fetchone()
        if session is None or session["status"] != "OPEN":
            raise StockError("盤點不存在或已完成")
        unfinished = connection.execute("""
            SELECT 1 FROM warehouse_count_items
            WHERE count_id = ? AND checked_at IS NULL LIMIT 1
        """, (count_id,)).fetchone()
        if unfinished:
            raise StockError("仍有未確認的儲位或批次")
        stale = connection.execute("""
            SELECT 1 FROM warehouse_count_items items
            LEFT JOIN stock_balances balances ON balances.lot_id = items.lot_id
              AND balances.location_id = items.location_id
            JOIN locations ON locations.id = items.location_id
            WHERE items.count_id = ? AND (locations.is_active = 0 OR
              (items.lot_id IS NOT NULL AND (balances.qty IS NULL OR balances.qty != items.original_qty)))
            LIMIT 1
        """, (count_id,)).fetchone()
        if stale:
            raise StockError("盤點期間庫存或儲位已變動，請取消並重新盤點")
        new_location = connection.execute("""
            SELECT 1 FROM locations
            JOIN warehouse_counts counts ON counts.warehouse_id = locations.warehouse_id
            WHERE counts.id = ? AND locations.is_active = 1 AND NOT EXISTS (
                SELECT 1 FROM warehouse_count_items items
                WHERE items.count_id = counts.id AND items.location_id = locations.id
            ) LIMIT 1
        """, (count_id,)).fetchone()
        if new_location:
            raise StockError("盤點期間新增了啟用儲位，請取消並重新盤點")
        changed = connection.execute("""
            SELECT 1 FROM stock_balances balances
            JOIN locations ON locations.id = balances.location_id
            JOIN warehouse_counts counts ON counts.warehouse_id = locations.warehouse_id
            WHERE counts.id = ? AND balances.qty > 0
              AND NOT EXISTS (
                SELECT 1 FROM warehouse_count_items items
                WHERE items.count_id = counts.id AND items.location_id = balances.location_id
                  AND items.lot_id = balances.lot_id
              ) LIMIT 1
        """, (count_id,)).fetchone()
        if changed:
            raise StockError("盤點開始後有新批次進入倉庫，請取消並重開盤點")
        connection.execute("""
            UPDATE warehouse_counts SET status = 'COMPLETE', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (count_id,))
        result = _session(connection, count_id)
    return result


def cancel_count(count_id: int) -> CountSession:
    with stock_transaction() as connection:
        updated = connection.execute("""
            UPDATE warehouse_counts SET status = 'CANCELLED', completed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'OPEN'
        """, (count_id,))
        if updated.rowcount != 1:
            raise StockError("盤點不存在或已結束")
        result = _session(connection, count_id)
    return result
