from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PositiveInt = Annotated[int, Field(strict=True, gt=0, le=9223372036854775807)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0, le=9223372036854775807)]


class AdjustmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lot_id: PositiveInt
    location_id: PositiveInt
    kind: Literal["COUNT", "SCRAP"]
    observed_qty: NonNegativeInt | None = None
    damaged_qty: PositiveInt | None = None
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_kind_fields(self) -> "AdjustmentCreate":
        if not self.reason.strip():
            raise ValueError("請填寫盤點或報廢原因")
        self.reason = self.reason.strip()
        if self.kind == "COUNT" and (self.observed_qty is None or self.damaged_qty is not None):
            raise ValueError("盤點須填非負整數實數，不可填報廢量")
        if self.kind == "SCRAP" and (self.damaged_qty is None or self.observed_qty is not None):
            raise ValueError("報廢須填正整數報廢量，不可填盤點實數")
        return self


class AdjustmentRecord(BaseModel):
    id: int
    kind: Literal["COUNT", "SCRAP"]
    lot_id: int
    lot_code: str
    product_name: str
    unit: str
    location_id: int
    location_code: str
    original_qty: int
    observed_qty: int | None
    damaged_qty: int | None
    reason: str
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    created_at: str
