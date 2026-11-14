# app/routers/helpers.py
# Job of this file: small shared pieces used by every router.

from typing import Annotated

from fastapi import Depends, Query

from app.core.deps import require_admin, require_staff
from app.models.user import User
from app.schemas.pagination import Page, PaginationParams

# Reads ?page=1&page_size=10 from the URL and validates it (page_size max 100).
Pagination = Annotated[PaginationParams, Query()]

# Shortcuts: "this route needs a staff/admin (or admin only) and gives me that user".
StaffUser = Annotated[User, Depends(require_staff)]
AdminUser = Annotated[User, Depends(require_admin)]


def make_page(rows, total: int, params: PaginationParams, schema) -> Page:
    """Wrap database rows in the Page reply. schema = e.g. PlanRead."""
    return Page[schema](
        items=[schema.model_validate(row) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )