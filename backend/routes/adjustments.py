from fastapi import APIRouter, Depends, HTTPException

from backend.auth import require_worker
from backend.schemas.adjustment import AdjustmentCreate, AdjustmentRecord
from backend.services.adjustment_service import create_adjustment, list_my_adjustments
from backend.services.auth_service import AuthenticatedUser
from backend.services.stock_service import StockError


router = APIRouter(prefix="/api/adjustments", tags=["adjustments"])


@router.post("", response_model=AdjustmentRecord, status_code=201)
def submit_adjustment(
    payload: AdjustmentCreate, user: AuthenticatedUser = Depends(require_worker)
) -> AdjustmentRecord:
    try:
        return create_adjustment(payload, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/mine", response_model=list[AdjustmentRecord])
def my_adjustments(
    user: AuthenticatedUser = Depends(require_worker),
) -> list[AdjustmentRecord]:
    return list_my_adjustments(user.id)
