from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

PositiveInt = Annotated[int, Field(strict=True, gt=0, le=9223372036854775807)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]


class CountStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    warehouse_id: PositiveInt


class CountCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observed_qty: NonNegativeInt
    note: str = Field(default="", max_length=500)


class CountBatchItem(CountCheck):
    item_id: PositiveInt


class CountBatchCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CountBatchItem] = Field(min_length=1)


class CountItem(BaseModel):
    id: int
    location_id: int
    location_code: str
    lot_id: int | None
    lot_code: str | None
    product_name: str | None
    unit: str | None
    original_qty: int
    observed_qty: int | None
    adjustment_request_id: int | None
    adjustment_status: Literal["PENDING", "APPROVED", "REJECTED"] | None
    checked_at: str | None
    note: str


class CountSession(BaseModel):
    id: int
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    created_by: int
    status: Literal["OPEN", "COMPLETE", "CANCELLED"]
    started_at: str
    completed_at: str | None
    items: list[CountItem]
