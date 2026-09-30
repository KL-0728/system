from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.outbound import PositiveInt

# Fixed UTC+8 so Windows does not need the optional tzdata package.
TAIWAN_TIME = timezone(timedelta(hours=8))


def taiwan_today() -> date:
    return datetime.now(TAIWAN_TIME).date()


class InboundCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: PositiveInt
    location_id: PositiveInt
    qty: PositiveInt
    received_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    received_at: datetime | None = None
    note: str = Field(default="", max_length=500)

    @field_validator("received_date")
    @classmethod
    def validate_calendar_date(cls, value: str) -> str:
        # The regex fixes the YYYY-MM-DD shape; this rejects dates such as 2026-02-30.
        try:
            received = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("入庫日期不是有效日期") from error
        if received > taiwan_today():
            raise ValueError("入庫日期不可晚於今天（臺灣時間）")
        return value

    @field_validator("received_at")
    @classmethod
    def validate_received_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("進貨時間必須包含時區")
        if value is not None and value > datetime.now(TAIWAN_TIME):
            raise ValueError("進貨時間不可晚於現在")
        return value


class InboundResult(BaseModel):
    lot_id: int
    lot_code: str
    product_id: int
    location_id: int
    received_date: str
    received_at: str | None = None
    qty: int
    movement_id: int


class InboundRecord(BaseModel):
    movement_id: int
    lot_id: int
    lot_code: str
    product_name: str
    unit: str
    received_date: str
    received_at: str | None = None
    location_id: int
    location_code: str
    qty: int
    actor_name: str
    note: str
    created_at: str
