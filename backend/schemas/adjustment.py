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


class AdjustmentDetail(AdjustmentRecord):
    requested_by: int
    requester_name: str
    current_qty: int
    difference: int
    reviewed_by: int | None
    reviewer_name: str | None
    review_note: str | None
    reviewed_at: str | None
    movement_id: int | None


class AdjustmentReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["APPROVE", "REJECT"]
    review_note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_review_note(self) -> "AdjustmentReview":
        self.review_note = self.review_note.strip()
        if self.action == "REJECT" and not self.review_note:
            raise ValueError("駁回必須填寫原因")
        return self


class AdjustmentReviewResult(BaseModel):
    request_id: int
    status: Literal["APPROVED", "REJECTED"]
    original_qty: int
    new_qty: int
    delta: int
    movement_id: int | None
    reviewed_by: int
    review_note: str
    reviewed_at: str
