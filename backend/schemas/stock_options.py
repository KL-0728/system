from pydantic import BaseModel


class LotOption(BaseModel):
    lot_id: int
    lot_code: str
    product_id: int
    product_name: str
    unit: str
    received_date: str
    total_qty: int


class BalanceOption(BaseModel):
    lot_id: int
    lot_code: str
    product_id: int
    product_name: str
    unit: str
    received_date: str
    location_id: int
    location_code: str
    warehouse_code: str
    qty: int
    has_pending: bool


class StockLocationOption(BaseModel):
    location_id: int
    location_code: str
    warehouse_code: str
    warehouse_name: str
