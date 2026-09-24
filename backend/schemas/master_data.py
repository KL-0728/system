from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: int
    name: str
    unit: str
    min_qty: int
    target_qty: int
    is_active: bool


class LocationResponse(BaseModel):
    id: int
    code: str
    is_active: bool
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
