# app/routers/complaints.py
# Job of this file: complaint endpoints (duplicates are detected in the service).

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.routers.helpers import Pagination, make_page
from app.schemas.complaint import (
    ComplaintCategory,
    ComplaintChannel,
    ComplaintCreate,
    ComplaintRead,
    ComplaintStatus,
    ComplaintUpdate,
)
from app.schemas.pagination import Page
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintRead, status_code=201)
def create_complaint(data: ComplaintCreate, db: DbSession, user: CurrentUser):
    return ComplaintService(db).create(data, user)


@router.get("", response_model=Page[ComplaintRead])
def list_complaints(
    params: Pagination,
    db: DbSession,
    user: CurrentUser,
    subscriber_id: int | None = None,
    status: ComplaintStatus | None = None,
    channel: ComplaintChannel | None = None,
    category: ComplaintCategory | None = None,
    duplicates_only: bool | None = None,
):
    """duplicates_only=true shows only copies, false shows only originals."""
    rows, total = ComplaintService(db).list(
        params.offset, params.page_size, user, subscriber_id, status, channel, category,
        duplicates_only,
    )
    return make_page(rows, total, params, ComplaintRead)


@router.get("/{complaint_id}", response_model=ComplaintRead)
def get_complaint(complaint_id: int, db: DbSession, user: CurrentUser):
    return ComplaintService(db).get(complaint_id, user)


@router.patch("/{complaint_id}/status", response_model=ComplaintRead)
def update_complaint_status(
    complaint_id: int, data: ComplaintUpdate, db: DbSession, user: CurrentUser
):
    """Staff/admin move a complaint along (the service refuses customers)."""
    return ComplaintService(db).update_status(complaint_id, data, user)