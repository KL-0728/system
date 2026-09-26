from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.outbound import PositiveInt


class ShortageDemandCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: PositiveInt
    qty: PositiveInt
    note: str = Field(default="", max_length=500)


class ShortageDemandRecord(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit: str
    qty: int
    note: str
    actor_name: str
    created_at: str


class ExpiryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_on: str | None

    @field_validator("expires_on")
    @classmethod
    def valid_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            valid = len(value) == 10 and date.fromisoformat(value).isoformat() == value
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("到期日須為 YYYY-MM-DD 的有效日期")
        return value


class ExpiryResult(BaseModel):
    lot_id: int
    lot_code: str
    expires_on: str | None
