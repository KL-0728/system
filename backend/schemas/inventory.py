from pydantic import BaseModel


class InventoryBalance(BaseModel):
    lot_id: int
    lot_code: str
    product_id: int
    product_name: str
    unit: str
    received_date: str
    expires_on: str | None
    expiry_status: str
    age_days: int
    received_by: str
    location_id: int
    location_code: str
    warehouse_code: str
    warehouse_name: str
    qty: int
    total_qty: int


class InventoryMovement(BaseModel):
    movement_id: int
    lot_id: int
    kind: str
    from_location_code: str | None
    to_location_code: str | None
    qty: int
    actor_name: str
    note: str
    adjustment_request_id: int | None
    created_at: str
