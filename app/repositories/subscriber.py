# app/repositories/subscriber.py
# Job of this file: database access for subscribers, including search and filters.

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.subscriber import Subscriber
from app.repositories.base import BaseRepository


class SubscriberRepository(BaseRepository[Subscriber]):
    def __init__(self, db: Session):
        super().__init__(db, Subscriber)

    def get_by_msisdn(self, msisdn: str) -> Subscriber | None:
        """Find a subscriber by phone number (used to stop duplicate numbers)."""
        return self.db.scalar(select(Subscriber).where(Subscriber.msisdn == msisdn))

    @staticmethod
    def build_filters(
        search: str | None = None,
        status: str | None = None,
        circle_id: int | None = None,
        plan_id: int | None = None,
        user_id: int | None = None,
    ) -> list[Any]:
        """Turn the filters into a list of conditions. None = skip that filter.
        user_id is the SECURITY filter: for end users the service always sets it
        to the logged-in user's id, so they only ever see their own numbers."""
        conditions: list[Any] = []

        if search:
            # or_ = either one matches: the name contains the text OR the number does.
            conditions.append(
                or_(
                    Subscriber.name.ilike(f"%{search}%"),
                    Subscriber.msisdn.like(f"%{search}%"),
                )
            )
        if status is not None:
            conditions.append(Subscriber.status == status)
        if circle_id is not None:
            conditions.append(Subscriber.circle_id == circle_id)
        if plan_id is not None:
            conditions.append(Subscriber.plan_id == plan_id)
        if user_id is not None:
            conditions.append(Subscriber.user_id == user_id)

        return conditions