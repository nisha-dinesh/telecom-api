# app/routers/admin.py
# Job of this file: admin-only maintenance endpoints.

from fastapi import APIRouter

from app.core.deps import DbSession
from app.routers.helpers import AdminUser
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/subscribers/fix-ported-out")
def fix_ported_out(db: DbSession, admin: AdminUser):
    """Clean ported-out numbers that still look active. Returns a summary."""
    return AdminService(db).fix_ported_out()