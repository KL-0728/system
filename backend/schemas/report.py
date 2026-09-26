from pydantic import BaseModel

from backend.schemas.extras import ShortageDemandRecord


class ReportSummary(BaseModel):
    active_product_count: int
    in_stock_product_count: int
    low_stock_product_count: int
    pending_adjustment_count: int
    shortage_demand_count: int


class ProductReport(BaseModel):
    product_id: int
    product_name: str
    unit: str
    current_qty: int
    min_qty: int
    target_qty: int
    is_low: bool
    replenishment_gap: int
    outbound_30d: int
    shortage_demand_qty: int
    count_gain_qty: int
    count_loss_qty: int
    scrap_qty: int


class AgedLotReport(BaseModel):
    lot_id: int
    lot_code: str
    product_name: str
    unit: str
    received_date: str
    age_days: int
    total_qty: int


class AdjustmentEventReport(BaseModel):
    movement_id: int
    adjustment_request_id: int
    kind: str
    lot_code: str
    product_name: str
    unit: str
    location_code: str
    qty: int
    actor_name: str
    reason: str
    created_at: str


class DecisionReport(BaseModel):
    as_of_utc: str
    summary: ReportSummary
    products: list[ProductReport]
    aged_lots: list[AgedLotReport]
    adjustments: list[AdjustmentEventReport]
    shortage_demands: list[ShortageDemandRecord]
