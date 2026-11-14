# app/services/usage_service.py
# Job of this file: business rules for usage records (data used per day).
# current_user is the logged-in User object (the router will pass it in).

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.repositories.subscriber import SubscriberRepository
from app.repositories.usage_record import UsageRecordRepository
from app.schemas.usage_record import UsageCreate, UsageSummary

MB_PER_GB = 1024  # same convention as plans: 1 GB = 1024 MB


def to_mb(raw_value: float, unit: str) -> float:
    """Convert what the source system sent into MB.
    round(..., 3) removes tiny float noise like 1536.0000000001."""
    if unit == "GB":
        return round(raw_value * MB_PER_GB, 3)
    return round(float(raw_value), 3)  # already MB


def _naive_utc(value: datetime) -> datetime:
    """The database stores times WITHOUT a timezone. If the client sent one,
    convert to UTC and drop it, so all times can be compared safely."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class UsageService:
    def __init__(self, db: Session):
        self.usage = UsageRecordRepository(db)
        self.subscribers = SubscriberRepository(db)

    @staticmethod
    def _is_customer(user: User) -> bool:
        """role 'user' = an end customer. 'staff' and 'admin' are employees."""
        return user.role == "user"

    def _get_subscriber(self, subscriber_id: int, current_user: User):
        """Find a subscriber; a customer asking for another's number gets 'not found' (BOLA)."""
        subscriber = self.subscribers.get(subscriber_id)
        if subscriber is None or (
            self._is_customer(current_user) and subscriber.user_id != current_user.id
        ):
            raise NotFoundError(f"Subscriber {subscriber_id} not found")
        return subscriber

    # ---------- read ----------

    def get(self, usage_id: int, current_user: User) -> UsageRecord:
        record = self.usage.get(usage_id)
        if record is None:
            raise NotFoundError(f"Usage record {usage_id} not found")
        # Reuse the ownership check: customers can only see usage of their own numbers.
        try:
            self._get_subscriber(record.subscriber_id, current_user)
        except NotFoundError:
            raise NotFoundError(f"Usage record {usage_id} not found")
        return record

    def list(
        self,
        offset: int,
        limit: int,
        current_user: User,
        subscriber_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> "tuple[list[UsageRecord], int]":
        # Security filter: a customer's list is ALWAYS limited to their own numbers.
        owner_id = current_user.id if self._is_customer(current_user) else None
        filters = UsageRecordRepository.build_filters(
            subscriber_id=subscriber_id,
            date_from=_naive_utc(date_from) if date_from else None,
            date_to=_naive_utc(date_to) if date_to else None,
            owner_user_id=owner_id,
        )
        return self.usage.get_many(offset=offset, limit=limit, filters=filters)

    def summary(self, subscriber_id: int, current_user: User) -> UsageSummary:
        """Total MB used and number of records for one number."""
        self._get_subscriber(subscriber_id, current_user)  # ownership check
        total_mb, count = self.usage.total_mb_for_subscriber(subscriber_id)
        return UsageSummary(subscriber_id=subscriber_id, total_mb=total_mb, record_count=count)

    # ---------- write ----------

    def create(self, data: UsageCreate, current_user: User) -> UsageRecord:
        # Only employees/network systems add usage, never the customer.
        if self._is_customer(current_user):
            raise ForbiddenError("Only staff or admin can add usage records")

        # Note: a ported_out number is allowed on purpose (real data is messy).
        self._get_subscriber(data.subscriber_id, current_user)

        usage_date = _naive_utc(data.usage_date)
        if usage_date > datetime.now(timezone.utc).replace(tzinfo=None):
            raise BusinessRuleError("Usage date cannot be in the future")

        return self.usage.add(
            UsageRecord(
                subscriber_id=data.subscriber_id,
                usage_date=usage_date,
                raw_value=data.raw_value,  # exactly what the source sent
                unit=data.unit,
                data_mb=to_mb(data.raw_value, data.unit),  # the server calculates this
            )
        )