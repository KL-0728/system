from pydantic import BaseModel, ConfigDict

from backend.schemas.outbound import PositiveInt


class TransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lot_id: PositiveInt
    from_location_id: PositiveInt
    to_location_id: PositiveInt
    qty: PositiveInt


class TransferResult(BaseModel):
    lot_id: int
    from_location_id: int
    to_location_id: int
    from_qty: int
    to_qty: int
    movement_id: int


class TransferRecord(BaseModel):
    movement_id: int
    lot_id: int
    lot_code: str
    product_name: str
    unit: str
    from_location_id: int
    from_location_code: str
    to_location_id: int
    to_location_code: str
    qty: int
    actor_name: str
    created_at: str
