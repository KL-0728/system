from fastapi import APIRouter, Depends

from backend.auth import require_admin
from backend.schemas.report import DecisionReport
from backend.services.auth_service import AuthenticatedUser
from backend.services.report_service import build_decision_report


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=DecisionReport)
def decision_report(
    _: AuthenticatedUser = Depends(require_admin),
) -> DecisionReport:
    return build_decision_report()
