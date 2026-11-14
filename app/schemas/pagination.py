# app/schemas/pagination.py
# Job of this file: shared "pages" logic used by every list endpoint.

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

# T is a placeholder for "any schema" (PlanRead, SubscriberRead, ...).
T = TypeVar("T")


class PaginationParams(BaseModel):
    """Which page the client wants.
    le=100 on page_size stops someone from asking for a million rows at once."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)

    @property
    def offset(self) -> int:
        # Page 1 skips 0 rows, page 2 skips page_size rows, and so on.
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    """A list wrapped with counts. Page[PlanRead] = a page of plans."""

    items: list[T]
    total: int  # how many rows exist in total (for all pages)
    page: int
    page_size: int