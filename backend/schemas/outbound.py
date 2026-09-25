from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

PositiveInt = Annotated[int, Field(strict=True, gt=0, le=9223372036854775807)]


class OutboundCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lot_id: PositiveInt
    location_id: PositiveInt
    qty: PositiveInt
    note: str = Field(default="", max_length=500)


class OutboundResult(BaseModel):
    lot_id: int
    location_id: int
    qty: int
    movement_id: int


class OutboundRecord(BaseModel):
    movement_id: int
    lot_id: int
    lot_code: str
    product_name: str
    unit: str
    location_id: int
    location_code: str
    qty: int
    actor_name: str
    note: str
    created_at: str
