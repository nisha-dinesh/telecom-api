# app/services/complaint_service.py
# Job of this file: business rules for complaints, including duplicate detection.
# current_user is the logged-in User object (the router will pass it in).

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.complaint import Complaint
from app.models.user import User
from app.repositories.complaint import ComplaintRepository
from app.repositories.subscriber import SubscriberRepository
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate


def make_dedupe_key(subscriber_id: int, category: str) -> str:
    """The 'fingerprint' of a complaint: subscriber | category | today's date (UTC).
    Channel is NOT part of it, so an app complaint and a call-centre complaint
    about the same problem get the SAME key."""
    today = datetime.now(timezone.utc).date().isoformat()
    return f"{subscriber_id}|{category}|{today}"


class ComplaintService:
    def __init__(self, db: Session):
        self.complaints = ComplaintRepository(db)
        self.subscribers = SubscriberRepository(db)

    @staticmethod
    def _is_customer(user: User) -> bool:
        """role 'user' = an end customer. 'staff' and 'admin' are employees."""
        return user.role == "user"

    # ---------- read ----------

    def get(self, complaint_id: int, current_user: User) -> Complaint:
        complaint = self.complaints.get(complaint_id)
        if complaint is None:
            raise NotFoundError(f"Complaint {complaint_id} not found")
        if self._is_customer(current_user):
            # A customer may only see complaints about their OWN numbers.
            subscriber = self.subscribers.get(complaint.subscriber_id)
            if subscriber is None or subscriber.user_id != current_user.id:
                raise NotFoundError(f"Complaint {complaint_id} not found")  # BOLA
        return complaint

    def list(
        self,
        offset: int,
        limit: int,
        current_user: User,
        subscriber_id: int | None = None,
        status: str | None = None,
        channel: str | None = None,
        category: str | None = None,
        duplicates_only: bool | None = None,
    ) -> "tuple[list[Complaint], int]":
        # Security filter: a customer's list is ALWAYS limited to their own numbers.
        owner_id = current_user.id if self._is_customer(current_user) else None
        filters = ComplaintRepository.build_filters(
            subscriber_id=subscriber_id,
            status=status,
            channel=channel,
            category=category,
            duplicates_only=duplicates_only,
            owner_user_id=owner_id,
        )
        return self.complaints.get_many(offset=offset, limit=limit, filters=filters)

    # ---------- write ----------

    def create(self, data: ComplaintCreate, current_user: User) -> Complaint:
        subscriber = self.subscribers.get(data.subscriber_id)
        # A customer cannot even learn that someone else's number exists.
        if subscriber is None or (
            self._is_customer(current_user) and subscriber.user_id != current_user.id
        ):
            raise NotFoundError(f"Subscriber {data.subscriber_id} not found")

        # Server builds the fingerprint, then looks for an earlier original.
        key = make_dedupe_key(data.subscriber_id, data.category)
        original = self.complaints.find_original(key)

        return self.complaints.add(
            Complaint(
                subscriber_id=data.subscriber_id,
                channel=data.channel,
                category=data.category,
                description=data.description.strip(),
                status="open",  # the client cannot choose this
                dedupe_key=key,
                # Found an original -> this one is a duplicate and points to it.
                linked_to_id=original.id if original else None,
            )
        )

    def update_status(
        self, complaint_id: int, data: ComplaintUpdate, current_user: User
    ) -> Complaint:
        """Staff/admin move a complaint along: open -> in_progress -> resolved -> closed."""
        if self._is_customer(current_user):
            raise ForbiddenError("Only staff or admin can update a complaint")
        complaint = self.get(complaint_id, current_user)
        return self.complaints.update(complaint, {"status": data.status})