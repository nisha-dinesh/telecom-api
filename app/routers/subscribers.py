# app/routers/subscribers.py
# Job of this file: subscriber endpoints. Customers only ever see their own numbers
# (the service enforces it); staff/admin see everyone.

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.routers.helpers import Pagination, make_page
from app.schemas.pagination import Page
from app.schemas.plan_change import ChangePlanRequest, PlanChangeRead
from app.schemas.subscriber import (
    SubscriberCreate,
    SubscriberRead,
    SubscriberStatus,
    SubscriberUpdate,
)
from app.services.subscriber_service import SubscriberService

router = APIRouter(prefix="/subscribers", tags=["Subscribers"])


@router.post("", response_model=SubscriberRead, status_code=201)
def create_subscriber(data: SubscriberCreate, db: DbSession, user: CurrentUser):
    return SubscriberService(db).create(data, user)


@router.get("", response_model=Page[SubscriberRead])
def list_subscribers(
    params: Pagination,
    db: DbSession,
    user: CurrentUser,
    search: Annotated[str | None, Query(max_length=100)] = None,
    status: SubscriberStatus | None = None,
    circle_id: int | None = None,
    plan_id: int | None = None,
):
    """Search by name or number; filter by status, circle, plan."""
    rows, total = SubscriberService(db).list(
        params.offset, params.page_size, user, search, status, circle_id, plan_id
    )
    return make_page(rows, total, params, SubscriberRead)


@router.get("/{subscriber_id}", response_model=SubscriberRead)
def get_subscriber(subscriber_id: int, db: DbSession, user: CurrentUser):
    return SubscriberService(db).get(subscriber_id, user)


@router.patch("/{subscriber_id}", response_model=SubscriberRead)
def update_subscriber(
    subscriber_id: int, data: SubscriberUpdate, db: DbSession, user: CurrentUser
):
    return SubscriberService(db).update(subscriber_id, data, user)


@router.delete("/{subscriber_id}", response_model=SubscriberRead)
def delete_subscriber(subscriber_id: int, db: DbSession, user: CurrentUser):
    """Soft delete: the number becomes 'inactive', the row stays."""
    return SubscriberService(db).delete(subscriber_id, user)


@router.post("/{subscriber_id}/change-plan", response_model=SubscriberRead)
def change_plan(
    subscriber_id: int, data: ChangePlanRequest, db: DbSession, user: CurrentUser
):
    return SubscriberService(db).change_plan(subscriber_id, data.new_plan_id, user)


@router.get("/{subscriber_id}/plan-history", response_model=list[PlanChangeRead])
def plan_history(subscriber_id: int, db: DbSession, user: CurrentUser):
    return SubscriberService(db).plan_history(subscriber_id, user)