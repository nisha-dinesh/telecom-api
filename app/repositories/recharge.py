# app/repositories/recharge.py
# Job of this file: database access for recharges, including filters.

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recharge import Recharge
from app.models.subscriber import Subscriber
from app.repositories.base import BaseRepository


class RechargeRepository(BaseRepository[Recharge]):
    def __init__(self, db: Session):
        super().__init__(db, Recharge)

    @staticmethod
    def build_filters(
        subscriber_id: int | None = None,
        plan_id: int | None = None,
        status: str | None = None,
        owner_user_id: int | None = None,
    ) -> list[Any]:
        """Turn the filters into a list of conditions. None = skip that filter.
        owner_user_id is the SECURITY filter: for end users the service sets it to
        the logged-in user's id, so they only see recharges of their OWN numbers."""
        conditions: list[Any] = []

        if subscriber_id is not None:
            conditions.append(Recharge.subscriber_id == subscriber_id)
        if plan_id is not None:
            conditions.append(Recharge.plan_id == plan_id)
        if status is not None:
            conditions.append(Recharge.status == status)
        if owner_user_id is not None:
            # A recharge has no user_id, so we ask: "is its subscriber one of
            # the subscribers that belong to this user?"
            own_subscriber_ids = select(Subscriber.id).where(
                Subscriber.user_id == owner_user_id
            )
            conditions.append(Recharge.subscriber_id.in_(own_subscriber_ids))

        return conditions