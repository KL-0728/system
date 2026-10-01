from fastapi import APIRouter, Depends, HTTPException, Path

from backend.auth import get_current_user, require_worker
from backend.schemas.warehouse_count import CountBatchCheck, CountCheck, CountSession, CountStart
from backend.services.auth_service import AuthenticatedUser
from backend.services.stock_service import StockError
from backend.services.warehouse_count_service import (
    cancel_count, check_all_items, check_item, complete_count, get_count, list_counts, reopen_item, start_count,
)

router = APIRouter(prefix="/api/warehouse-counts", tags=["warehouse-counts"])


@router.get("", response_model=list[CountSession])
def counts(_: AuthenticatedUser = Depends(get_current_user)) -> list[CountSession]:
    return list_counts()


@router.post("", response_model=CountSession, status_code=201)
def start(payload: CountStart, user: AuthenticatedUser = Depends(require_worker)) -> CountSession:
    try:
        return start_count(payload.warehouse_id, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{count_id}", response_model=CountSession)
def detail(count_id: int = Path(gt=0, le=9223372036854775807), _: AuthenticatedUser = Depends(get_current_user)) -> CountSession:
    result = get_count(count_id)
    if result is None:
        raise HTTPException(status_code=404, detail="找不到盤點")
    return result


@router.post("/{count_id}/items/{item_id}", response_model=CountSession)
def check(
    payload: CountCheck,
    count_id: int = Path(gt=0, le=9223372036854775807),
    item_id: int = Path(gt=0, le=9223372036854775807),
    user: AuthenticatedUser = Depends(require_worker),
) -> CountSession:
    try:
        return check_item(count_id, item_id, payload.observed_qty, payload.note, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{count_id}/check-all", response_model=CountSession)
def check_all(
    payload: CountBatchCheck,
    count_id: int = Path(gt=0, le=9223372036854775807),
    user: AuthenticatedUser = Depends(require_worker),
) -> CountSession:
    try:
        return check_all_items(count_id, payload.items, user.id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{count_id}/items/{item_id}/reopen", response_model=CountSession)
def reopen(
    count_id: int = Path(gt=0, le=9223372036854775807),
    item_id: int = Path(gt=0, le=9223372036854775807),
    _: AuthenticatedUser = Depends(require_worker),
) -> CountSession:
    try:
        return reopen_item(count_id, item_id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{count_id}/complete", response_model=CountSession)
def complete(count_id: int = Path(gt=0, le=9223372036854775807), _: AuthenticatedUser = Depends(require_worker)) -> CountSession:
    try:
        return complete_count(count_id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{count_id}/cancel", response_model=CountSession)
def cancel(count_id: int = Path(gt=0, le=9223372036854775807), _: AuthenticatedUser = Depends(require_worker)) -> CountSession:
    try:
        return cancel_count(count_id)
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
