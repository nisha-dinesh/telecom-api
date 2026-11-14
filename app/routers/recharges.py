# app/routers/recharges.py
# Job of this file: recharge endpoints. The price always comes from the plan.

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.routers.helpers import Pagination, make_page
from app.schemas.pagination import Page
from app.schemas.recharge import (
    RechargeCreate,
    RechargeRead,
    RechargeStatus,
    RechargeStatusUpdate,
)
from app.services.recharge_service import RechargeService

router = APIRouter(prefix="/recharges", tags=["Recharges"])


@router.post("", response_model=RechargeRead, status_code=201)
def create_recharge(data: RechargeCreate, db: DbSession, user: CurrentUser):
    return RechargeService(db).create(data, user)


@router.get("", response_model=Page[RechargeRead])
def list_recharges(
    params: Pagination,
    db: DbSession,
    user: CurrentUser,
    subscriber_id: int | None = None,
    plan_id: int | None = None,
    status: RechargeStatus | None = None,
):
    rows, total = RechargeService(db).list(
        params.offset, params.page_size, user, subscriber_id, plan_id, status
    )
    return make_page(rows, total, params, RechargeRead)


@router.get("/{recharge_id}", response_model=RechargeRead)
def get_recharge(recharge_id: int, db: DbSession, user: CurrentUser):
    return RechargeService(db).get(recharge_id, user)


@router.patch("/{recharge_id}/status", response_model=RechargeRead)
def update_recharge_status(
    recharge_id: int, data: RechargeStatusUpdate, db: DbSession, user: CurrentUser
):
    """Staff/admin record the payment result (the service refuses customers)."""
    return RechargeService(db).update_status(recharge_id, data, user)