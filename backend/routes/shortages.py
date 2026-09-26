from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user, require_worker
from backend.schemas.extras import ShortageDemandCreate, ShortageDemandRecord
from backend.services.auth_service import AuthenticatedUser
from backend.services.extra_service import create_shortage_demand, list_shortage_demands
from backend.services.stock_service import StockError


router = APIRouter(prefix="/api/shortages", tags=["shortages"])


@router.post("", response_model=ShortageDemandRecord, status_code=201)
def create_demand(
    payload: ShortageDemandCreate,
    user: AuthenticatedUser = Depends(require_worker),
) -> ShortageDemandRecord:
    try:
        return create_shortage_demand(payload, user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except StockError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[ShortageDemandRecord])
def demand_records(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[ShortageDemandRecord]:
    return list_shortage_demands(None if user.role == "ADMIN" else user.id)
