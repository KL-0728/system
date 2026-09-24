from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.database import connect_database
from backend.schemas.master_data import LocationResponse, ProductResponse
from backend.services.auth_service import AuthenticatedUser


router = APIRouter(prefix="/api/master-data", tags=["master-data"])


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ProductResponse]:
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT id, name, unit, min_qty, target_qty, is_active
            FROM products
            ORDER BY name COLLATE NOCASE, id
            """
        ).fetchall()
    return [ProductResponse(**{**dict(row), "is_active": bool(row["is_active"])}) for row in rows]


@router.get("/locations", response_model=list[LocationResponse])
def list_locations(
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[LocationResponse]:
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT l.id, l.code, l.is_active, w.id AS warehouse_id,
                   w.code AS warehouse_code, w.name AS warehouse_name
            FROM locations AS l
            JOIN warehouses AS w ON w.id = l.warehouse_id
            ORDER BY w.code, l.code
            """
        ).fetchall()
    return [LocationResponse(**{**dict(row), "is_active": bool(row["is_active"])}) for row in rows]
