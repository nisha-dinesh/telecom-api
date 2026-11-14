# app/repositories/complaint.py
# Job of this file: database access for complaints, including the lookup
# that powers duplicate detection (find_original).

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.subscriber import Subscriber
from app.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository[Complaint]):
    def __init__(self, db: Session):
        super().__init__(db, Complaint)

    def find_original(self, dedupe_key: str) -> Complaint | None:
        """Find the ORIGINAL complaint for a fingerprint.
        Original = same dedupe_key AND linked_to_id is empty (it is not a copy itself).
        If there are several, take the oldest one (lowest id).
        The service uses this: found -> new complaint is a duplicate; None -> it is the original."""
        return self.db.scalar(
            select(Complaint)
            .where(Complaint.dedupe_key == dedupe_key)
            .where(Complaint.linked_to_id.is_(None))
            .order_by(Complaint.id)
            .limit(1)
        )

    @staticmethod
    def build_filters(
        subscriber_id: int | None = None,
        status: str | None = None,
        channel: str | None = None,
        category: str | None = None,
        duplicates_only: bool | None = None,
        owner_user_id: int | None = None,
    ) -> list[Any]:
        """Turn the filters into a list of conditions. None = skip that filter.
        owner_user_id is the SECURITY filter (end users see only their own complaints)."""
        conditions: list[Any] = []

        if subscriber_id is not None:
            conditions.append(Complaint.subscriber_id == subscriber_id)
        if status is not None:
            conditions.append(Complaint.status == status)
        if channel is not None:
            conditions.append(Complaint.channel == channel)
        if category is not None:
            conditions.append(Complaint.category == category)
        if duplicates_only is True:
            # Only copies: they point to an original.
            conditions.append(Complaint.linked_to_id.is_not(None))
        elif duplicates_only is False:
            # Only originals: they do not point to anything.
            conditions.append(Complaint.linked_to_id.is_(None))
        if owner_user_id is not None:
            own_subscriber_ids = select(Subscriber.id).where(
                Subscriber.user_id == owner_user_id
            )
            conditions.append(Complaint.subscriber_id.in_(own_subscriber_ids))

        return conditions