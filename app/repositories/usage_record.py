# app/repositories/usage_record.py
# Job of this file: database access for usage records, including the
# "total MB used" sum. Because every row has data_mb (already converted),
# rows that were sent in MB and in GB can be added together fairly.

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.subscriber import Subscriber
from app.models.usage_record import UsageRecord
from app.repositories.base import BaseRepository


class UsageRecordRepository(BaseRepository[UsageRecord]):
    def __init__(self, db: Session):
        super().__init__(db, UsageRecord)

    @staticmethod
    def build_filters(
        subscriber_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        owner_user_id: int | None = None,
    ) -> list[Any]:
        """Turn the filters into a list of conditions. None = skip that filter.
        owner_user_id is the SECURITY filter (end users see only their own usage)."""
        conditions: list[Any] = []

        if subscriber_id is not None:
            conditions.append(UsageRecord.subscriber_id == subscriber_id)
        if date_from is not None:
            conditions.append(UsageRecord.usage_date >= date_from)
        if date_to is not None:
            conditions.append(UsageRecord.usage_date <= date_to)
        if owner_user_id is not None:
            own_subscriber_ids = select(Subscriber.id).where(
                Subscriber.user_id == owner_user_id
            )
            conditions.append(UsageRecord.subscriber_id.in_(own_subscriber_ids))

        return conditions

    def total_mb_for_subscriber(self, subscriber_id: int) -> tuple[float, int]:
        """Return (total MB used, number of records) for one subscriber.
        coalesce(..., 0.0) = use 0 if the subscriber has no records at all."""
        row = self.db.execute(
            select(
                func.coalesce(func.sum(UsageRecord.data_mb), 0.0),
                func.count(UsageRecord.id),
            ).where(UsageRecord.subscriber_id == subscriber_id)
        ).one()
        return float(row[0]), int(row[1])