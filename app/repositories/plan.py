# app/repositories/plan.py
# Job of this file: database access for plans, including search and filters.

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    def __init__(self, db: Session):
        super().__init__(db, Plan)

    @staticmethod
    def build_filters(
        search: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        min_data_mb: int | None = None,
        is_active: bool | None = None,
    ) -> list[Any]:
        """Turn the filters the client sent into a list of conditions.
        A filter that is None (not sent) is simply skipped."""
        conditions: list[Any] = []

        if search:
            # ilike = case-insensitive "contains". %text% = text anywhere in the name.
            conditions.append(Plan.name.ilike(f"%{search}%"))
        if min_price is not None:
            conditions.append(Plan.price >= min_price)
        if max_price is not None:
            conditions.append(Plan.price <= max_price)
        if min_data_mb is not None:
            conditions.append(Plan.data_mb_per_day >= min_data_mb)
        if is_active is not None:
            conditions.append(Plan.is_active == is_active)

        return conditions