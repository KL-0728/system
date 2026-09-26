from fastapi import APIRouter, Depends, HTTPException, Path

from backend.auth import require_admin, require_worker
from backend.schemas.adjustment import (
    AdjustmentCreate, AdjustmentDetail, AdjustmentRecord,
    AdjustmentReview, AdjustmentReviewResult,
)
from backend.services.adjustment_service import (
    create_adjustment, get_adjustment_detail, list_my_adjustments,
    list_pending_adjustments, list_reviewed_adjustments, review_adjustment,
)
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


@router.get("/pending", response_model=list[AdjustmentDetail])
def pending_adjustments(
    _: AuthenticatedUser = Depends(require_admin),
) -> list[AdjustmentDetail]:
    return list_pending_adjustments()


@router.get("/reviewed", response_model=list[AdjustmentDetail])
def reviewed_adjustments(
    _: AuthenticatedUser = Depends(require_admin),
) -> list[AdjustmentDetail]:
    return list_reviewed_adjustments()


@router.get("/{request_id}", response_model=AdjustmentDetail)
def adjustment_detail(
    request_id: int = Path(gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(require_admin),
) -> AdjustmentDetail:
    detail = get_adjustment_detail(request_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="找不到指定申請")
    return detail


@router.post("/{request_id}/review", response_model=AdjustmentReviewResult)
def review(
    payload: AdjustmentReview,
    request_id: int = Path(gt=0, le=9223372036854775807),
    user: AuthenticatedUser = Depends(require_admin),
) -> AdjustmentReviewResult:
    try:
        return review_adjustment(request_id, payload, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
