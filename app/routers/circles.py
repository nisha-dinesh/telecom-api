# app/routers/circles.py
# Job of this file: circle endpoints. Read = any logged-in user, write = staff/admin.

from fastapi import APIRouter, Response

from app.core.deps import CurrentUser, DbSession
from app.routers.helpers import Pagination, StaffUser, make_page
from app.schemas.circle import CircleCreate, CircleRead, CircleUpdate
from app.schemas.pagination import Page
from app.services.circle_service import CircleService

router = APIRouter(prefix="/circles", tags=["Circles"])


@router.post("", response_model=CircleRead, status_code=201)
def create_circle(data: CircleCreate, db: DbSession, staff: StaffUser):
    return CircleService(db).create(data)


@router.get("", response_model=Page[CircleRead])
def list_circles(params: Pagination, db: DbSession, user: CurrentUser):
    rows, total = CircleService(db).list(params.offset, params.page_size)
    return make_page(rows, total, params, CircleRead)


@router.get("/{circle_id}", response_model=CircleRead)
def get_circle(circle_id: int, db: DbSession, user: CurrentUser):
    return CircleService(db).get(circle_id)


@router.put("/{circle_id}", response_model=CircleRead)
def update_circle(circle_id: int, data: CircleUpdate, db: DbSession, staff: StaffUser):
    return CircleService(db).update(circle_id, data)


@router.delete("/{circle_id}", status_code=204)
def delete_circle(circle_id: int, db: DbSession, staff: StaffUser):
    CircleService(db).delete(circle_id)
    return Response(status_code=204)  # 204 = done, nothing to send back