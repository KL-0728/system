from pydantic import BaseModel, Field, model_validator


class ProductWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=30)
    min_qty: int = Field(ge=0)
    target_qty: int = Field(ge=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_target(self) -> "ProductWrite":
        self.name = self.name.strip()
        self.unit = self.unit.strip()
        if not self.name or not self.unit:
            raise ValueError("品項名稱與單位不可空白")
        if self.target_qty < self.min_qty:
            raise ValueError("目標量不得低於最低量")
        return self


class LocationWrite(BaseModel):
    warehouse_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=30)
    is_active: bool = True

    @model_validator(mode="after")
    def normalize_code(self) -> "LocationWrite":
        self.code = self.code.strip().upper()
        if not self.code:
            raise ValueError("儲位代碼不可空白")
        return self


class WarehouseResponse(BaseModel):
    id: int
    code: str
    name: str


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
