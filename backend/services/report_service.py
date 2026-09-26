from datetime import date, datetime, timedelta, timezone

from backend.database import connect_database
from backend.schemas.extras import ShortageDemandRecord
from backend.schemas.report import (
    AdjustmentEventReport, AgedLotReport, DecisionReport,
    ProductReport, ReportSummary,
)


def build_decision_report(as_of: datetime | None = None) -> DecisionReport:
    """Read one SQLite snapshot using one server UTC cutoff for the 30-day window."""
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("報表時間必須包含時區")
    now = now.astimezone(timezone.utc)
    start = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")
    taiwan_today = now.astimezone(timezone(timedelta(hours=8))).date()

    with connect_database() as connection:
        connection.execute("BEGIN")
        product_rows = connection.execute(
            """
            WITH stock_totals AS (
                SELECT lots.product_id, SUM(balances.qty) AS qty
                FROM lots JOIN stock_balances AS balances ON balances.lot_id = lots.id
                GROUP BY lots.product_id
            ), outbound_totals AS (
                SELECT lots.product_id, SUM(movements.qty) AS qty
                FROM stock_movements AS movements
                JOIN lots ON lots.id = movements.lot_id
                WHERE movements.kind = 'OUTBOUND'
                  AND movements.created_at >= ? AND movements.created_at <= ?
                GROUP BY lots.product_id
            ), shortage_totals AS (
                SELECT product_id, SUM(qty) AS qty
                FROM shortage_demands GROUP BY product_id
            ), adjustment_totals AS (
                SELECT lots.product_id,
                       SUM(CASE WHEN movements.kind = 'COUNT_GAIN' THEN movements.qty ELSE 0 END) AS count_gain_qty,
                       SUM(CASE WHEN movements.kind = 'COUNT_LOSS' THEN movements.qty ELSE 0 END) AS count_loss_qty,
                       SUM(CASE WHEN movements.kind = 'SCRAP' THEN movements.qty ELSE 0 END) AS scrap_qty
                FROM stock_movements AS movements
                JOIN adjustment_requests AS requests
                  ON requests.id = movements.adjustment_request_id AND requests.status = 'APPROVED'
                JOIN lots ON lots.id = movements.lot_id
                WHERE movements.kind IN ('COUNT_GAIN', 'COUNT_LOSS', 'SCRAP')
                GROUP BY lots.product_id
            )
            SELECT products.id AS product_id, products.name AS product_name, products.unit,
                   products.min_qty, products.target_qty,
                   COALESCE(stock_totals.qty, 0) AS current_qty,
                   COALESCE(outbound_totals.qty, 0) AS outbound_30d,
                   COALESCE(shortage_totals.qty, 0) AS shortage_demand_qty,
                   COALESCE(adjustment_totals.count_gain_qty, 0) AS count_gain_qty,
                   COALESCE(adjustment_totals.count_loss_qty, 0) AS count_loss_qty,
                   COALESCE(adjustment_totals.scrap_qty, 0) AS scrap_qty
            FROM products
            LEFT JOIN stock_totals ON stock_totals.product_id = products.id
            LEFT JOIN outbound_totals ON outbound_totals.product_id = products.id
            LEFT JOIN shortage_totals ON shortage_totals.product_id = products.id
            LEFT JOIN adjustment_totals ON adjustment_totals.product_id = products.id
            WHERE products.is_active = 1
            ORDER BY products.name, products.id
            """,
            (start, end),
        ).fetchall()
        pending_count = connection.execute(
            "SELECT COUNT(*) FROM adjustment_requests WHERE status = 'PENDING'"
        ).fetchone()[0]
        shortage_count = connection.execute("SELECT COUNT(*) FROM shortage_demands").fetchone()[0]
        shortage_rows = connection.execute("""
            SELECT demands.id, demands.product_id, products.name AS product_name,
                   products.unit, demands.qty, demands.note,
                   users.display_name AS actor_name,
                   strftime('%Y-%m-%dT%H:%M:%SZ', demands.created_at) AS created_at
            FROM shortage_demands AS demands
            JOIN products ON products.id = demands.product_id
            JOIN users ON users.id = demands.actor_id
            ORDER BY demands.id DESC LIMIT 100
        """).fetchall()
        lot_rows = connection.execute(
            """
            SELECT lots.id AS lot_id, lots.lot_code, products.name AS product_name,
                   products.unit, lots.received_date, SUM(balances.qty) AS total_qty
            FROM lots
            JOIN products ON products.id = lots.product_id
            JOIN stock_balances AS balances ON balances.lot_id = lots.id
            GROUP BY lots.id
            HAVING SUM(balances.qty) > 0
            ORDER BY lots.received_date ASC, lots.lot_code
            """
        ).fetchall()
        event_rows = connection.execute(
            """
            SELECT movements.id AS movement_id,
                   movements.adjustment_request_id, movements.kind,
                   lots.lot_code, products.name AS product_name, products.unit,
                   locations.code AS location_code, movements.qty,
                   users.display_name AS actor_name, requests.reason,
                   strftime('%Y-%m-%dT%H:%M:%SZ', movements.created_at) AS created_at
            FROM stock_movements AS movements
            JOIN adjustment_requests AS requests
              ON requests.id = movements.adjustment_request_id AND requests.status = 'APPROVED'
            JOIN lots ON lots.id = movements.lot_id
            JOIN products ON products.id = lots.product_id
            JOIN locations ON locations.id = COALESCE(movements.from_location_id, movements.to_location_id)
            JOIN users ON users.id = movements.actor_id
            WHERE movements.kind IN ('COUNT_GAIN', 'COUNT_LOSS', 'SCRAP')
            ORDER BY movements.id DESC
            """
        ).fetchall()

    products = [ProductReport(
        **dict(row),
        is_low=row["current_qty"] < row["min_qty"],
        replenishment_gap=max(row["target_qty"] - row["current_qty"], 0),
    ) for row in product_rows]
    aged_lots = [AgedLotReport(
        **dict(row),
        age_days=max((taiwan_today - date.fromisoformat(row["received_date"])).days, 0),
    ) for row in lot_rows]
    return DecisionReport(
        as_of_utc=now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        summary=ReportSummary(
            active_product_count=len(products),
            in_stock_product_count=sum(product.current_qty > 0 for product in products),
            low_stock_product_count=sum(product.is_low for product in products),
            pending_adjustment_count=pending_count,
            shortage_demand_count=shortage_count,
        ),
        products=products,
        aged_lots=aged_lots,
        adjustments=[AdjustmentEventReport(**dict(row)) for row in event_rows],
        shortage_demands=[ShortageDemandRecord(**dict(row)) for row in shortage_rows],
    )
