# app/routers/plans.py
# Job of this file: plan endpoints, including search and filters (plan comparison).

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.routers.helpers import AdminUser, Pagination, StaffUser, make_page
from app.schemas.pagination import Page
from app.schemas.plan import PlanCreate, PlanRead, PlanUpdate
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.post("", response_model=PlanRead, status_code=201)
def create_plan(data: PlanCreate, db: DbSession, staff: StaffUser):
    return PlanService(db).create(data)


@router.get("", response_model=Page[PlanRead])
def list_plans(
    params: Pagination,
    db: DbSession,
    user: CurrentUser,
    search: Annotated[str | None, Query(max_length=100)] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    min_data_mb: Annotated[int | None, Query(ge=0)] = None,
    is_active: bool | None = None,
):
    """Search by name and filter by price range, minimum data per day, active flag."""
    rows, total = PlanService(db).list(
        params.offset, params.page_size, search, min_price, max_price, min_data_mb, is_active
    )
    return make_page(rows, total, params, PlanRead)


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: int, db: DbSession, user: CurrentUser):
    return PlanService(db).get(plan_id)


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: int, data: PlanUpdate, db: DbSession, staff: StaffUser):
    return PlanService(db).update(plan_id, data)


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: DbSession, admin: AdminUser):
    """Deletes an unused plan, or only deactivates a plan that is already in use."""
    return {"result": PlanService(db).delete(plan_id)}