# app/routers/usage.py
# Job of this file: usage endpoints (data used), plus the total-MB summary.

from datetime import datetime

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.routers.helpers import Pagination, make_page
from app.schemas.pagination import Page
from app.schemas.usage_record import UsageCreate, UsageRead, UsageSummary
from app.services.usage_service import UsageService

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.post("", response_model=UsageRead, status_code=201)
def create_usage(data: UsageCreate, db: DbSession, user: CurrentUser):
    """Staff/admin add usage. data_mb is calculated by the server."""
    return UsageService(db).create(data, user)


@router.get("", response_model=Page[UsageRead])
def list_usage(
    params: Pagination,
    db: DbSession,
    user: CurrentUser,
    subscriber_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    rows, total = UsageService(db).list(
        params.offset, params.page_size, user, subscriber_id, date_from, date_to
    )
    return make_page(rows, total, params, UsageRead)


@router.get("/summary/{subscriber_id}", response_model=UsageSummary)
def usage_summary(
    subscriber_id: int,
    db: DbSession,
    user: CurrentUser,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    return UsageService(db).summary(subscriber_id, user, date_from, date_to)

@router.get("/{usage_id}", response_model=UsageRead)
def get_usage(usage_id: int, db: DbSession, user: CurrentUser):
    return UsageService(db).get(usage_id, user)