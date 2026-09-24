from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import get_current_user, require_admin
from backend.database import connect_database
from backend.schemas.master_data import (
    LocationResponse,
    LocationWrite,
    ProductResponse,
    ProductWrite,
    WarehouseResponse,
)
from backend.services.auth_service import AuthenticatedUser
from backend.services.master_data_service import (
    MasterDataConflict,
    MasterDataNotFound,
    create_location,
    create_product,
    update_location,
    update_product,
)


router = APIRouter(prefix="/api/master-data", tags=["master-data"])


def _run_write(action):
    with connect_database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            result = action(connection)
            connection.commit()
            return result
        except MasterDataNotFound as error:
            connection.rollback()
            raise HTTPException(status_code=404, detail=str(error)) from error
        except MasterDataConflict as error:
            connection.rollback()
            raise HTTPException(status_code=409, detail=str(error)) from error
        except BaseException:
            connection.rollback()
            raise


def _get_product(product_id: int) -> ProductResponse:
    with connect_database() as connection:
        row = connection.execute(
            "SELECT id, name, unit, min_qty, target_qty, is_active FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到品項")
    return ProductResponse(**{**dict(row), "is_active": bool(row["is_active"])})


def _get_location(location_id: int) -> LocationResponse:
    with connect_database() as connection:
        row = connection.execute(
            """
            SELECT l.id, l.code, l.is_active, w.id AS warehouse_id,
                   w.code AS warehouse_code, w.name AS warehouse_name
            FROM locations AS l JOIN warehouses AS w ON w.id = l.warehouse_id
            WHERE l.id = ?
            """,
            (location_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到儲位")
    return LocationResponse(**{**dict(row), "is_active": bool(row["is_active"])})


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


@router.get("/warehouses", response_model=list[WarehouseResponse])
def list_warehouses(
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[WarehouseResponse]:
    with connect_database() as connection:
        rows = connection.execute(
            "SELECT id, code, name FROM warehouses ORDER BY code"
        ).fetchall()
    return [WarehouseResponse(**dict(row)) for row in rows]


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(
    data: ProductWrite,
    _: AuthenticatedUser = Depends(require_admin),
) -> ProductResponse:
    product_id = _run_write(lambda connection: create_product(connection, data))
    return _get_product(product_id)


@router.put("/products/{product_id}", response_model=ProductResponse)
def edit_product(
    product_id: int,
    data: ProductWrite,
    _: AuthenticatedUser = Depends(require_admin),
) -> ProductResponse:
    _run_write(lambda connection: update_product(connection, product_id, data))
    return _get_product(product_id)


@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def add_location(
    data: LocationWrite,
    _: AuthenticatedUser = Depends(require_admin),
) -> LocationResponse:
    location_id = _run_write(lambda connection: create_location(connection, data))
    return _get_location(location_id)


@router.put("/locations/{location_id}", response_model=LocationResponse)
def edit_location(
    location_id: int,
    data: LocationWrite,
    _: AuthenticatedUser = Depends(require_admin),
) -> LocationResponse:
    _run_write(lambda connection: update_location(connection, location_id, data))
    return _get_location(location_id)
