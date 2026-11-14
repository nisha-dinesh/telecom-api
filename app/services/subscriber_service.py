# app/services/subscriber_service.py
# Job of this file: business rules for subscribers (mobile numbers).
# current_user is the logged-in User object (the router will pass it in).

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.models.plan import Plan
from app.models.plan_change import PlanChange
from app.models.subscriber import Subscriber
from app.models.user import User
from app.repositories.circle import CircleRepository
from app.repositories.plan import PlanRepository
from app.repositories.plan_change import PlanChangeRepository
from app.repositories.subscriber import SubscriberRepository
from app.repositories.user import UserRepository
from app.schemas.subscriber import SubscriberCreate, SubscriberUpdate


class SubscriberService:
    def __init__(self, db: Session):
        self.subscribers = SubscriberRepository(db)
        self.circles = CircleRepository(db)
        self.plans = PlanRepository(db)
        self.users = UserRepository(db)
        self.changes = PlanChangeRepository(db)

    # ---------- small helpers ----------

    @staticmethod
    def _is_customer(user: User) -> bool:
        """role 'user' = an end customer. 'staff' and 'admin' are employees."""
        return user.role == "user"

    def _get_active_plan(self, plan_id: int) -> Plan:
        plan = self.plans.get(plan_id)
        if plan is None:
            raise NotFoundError(f"Plan {plan_id} not found")
        if not plan.is_active:
            raise BusinessRuleError(f"Plan {plan_id} is not active")
        return plan

    # ---------- read ----------

    def get(self, subscriber_id: int, current_user: User) -> Subscriber:
        subscriber = self.subscribers.get(subscriber_id)
        # A customer asking for someone else's number gets "not found" (not
        # "forbidden"), so they cannot learn which subscriber ids exist (BOLA).
        if subscriber is None or (
            self._is_customer(current_user) and subscriber.user_id != current_user.id
        ):
            raise NotFoundError(f"Subscriber {subscriber_id} not found")
        return subscriber

    def list(
        self,
        offset: int,
        limit: int,
        current_user: User,
        search: str | None = None,
        status: str | None = None,
        circle_id: int | None = None,
        plan_id: int | None = None,
    ) -> tuple[list[Subscriber], int]:
        # Security filter: a customer's list is ALWAYS limited to their own numbers.
        owner_id = current_user.id if self._is_customer(current_user) else None
        filters = SubscriberRepository.build_filters(
            search=search,
            status=status,
            circle_id=circle_id,
            plan_id=plan_id,
            user_id=owner_id,
        )
        return self.subscribers.get_many(offset=offset, limit=limit, filters=filters)

    def plan_history(self, subscriber_id: int, current_user: User) -> "list[PlanChange]":
        self.get(subscriber_id, current_user)  # also runs the ownership check
        return self.changes.list_for_subscriber(subscriber_id)

    # ---------- write ----------

    def create(self, data: SubscriberCreate, current_user: User) -> Subscriber:
        if self._is_customer(current_user):
            owner_id = current_user.id  # a customer can only add numbers for themselves
        else:
            if data.user_id is None:
                raise BusinessRuleError("user_id is required when staff or admin add a subscriber")
            if self.users.get(data.user_id) is None:
                raise NotFoundError(f"User {data.user_id} not found")
            owner_id = data.user_id

        if self.subscribers.get_by_msisdn(data.msisdn):
            raise ConflictError(f"Phone number {data.msisdn} is already registered")
        if self.circles.get(data.circle_id) is None:
            raise NotFoundError(f"Circle {data.circle_id} not found")
        if data.plan_id is not None:
            self._get_active_plan(data.plan_id)

        subscriber = self.subscribers.add(
            Subscriber(
                user_id=owner_id,
                msisdn=data.msisdn,
                name=data.name.strip(),
                circle_id=data.circle_id,
                plan_id=data.plan_id,
                status="active",  # the client cannot choose this
            )
        )
        # The first plan is also history (old plan = None).
        if data.plan_id is not None:
            self.changes.add(
                PlanChange(
                    subscriber_id=subscriber.id,
                    old_plan_id=None,
                    new_plan_id=data.plan_id,
                )
            )
        return subscriber

    def change_plan(self, subscriber_id: int, new_plan_id: int, current_user: User) -> Subscriber:
        """Switch plan and write a history row. A customer may do this for their own number."""
        subscriber = self.get(subscriber_id, current_user)
        if subscriber.status == "ported_out":
            raise BusinessRuleError("A ported-out number cannot change plan")
        self._get_active_plan(new_plan_id)
        if subscriber.plan_id == new_plan_id:
            raise BusinessRuleError("Subscriber is already on this plan")

        old_plan_id = subscriber.plan_id
        self.subscribers.update(subscriber, {"plan_id": new_plan_id})
        self.changes.add(
            PlanChange(
                subscriber_id=subscriber.id,
                old_plan_id=old_plan_id,
                new_plan_id=new_plan_id,
            )
        )
        return subscriber

    def update(self, subscriber_id: int, data: SubscriberUpdate, current_user: User) -> Subscriber:
        """Staff/admin edit a subscriber (name, circle, plan, status)."""
        if self._is_customer(current_user):
            raise ForbiddenError("Only staff or admin can edit subscribers")
        subscriber = self.get(subscriber_id, current_user)

        raw = data.model_dump(exclude_unset=True)  # only what the client sent
        if "plan_id" in raw and raw["plan_id"] is None:
            raise BusinessRuleError("plan_id cannot be empty; choose a plan")
        changes = {key: value for key, value in raw.items() if value is not None}

        if subscriber.status == "ported_out" and changes.get("status") in ("active", "inactive"):
            raise BusinessRuleError("A ported-out number cannot be reactivated")
        if "circle_id" in changes and self.circles.get(changes["circle_id"]) is None:
            raise NotFoundError(f"Circle {changes['circle_id']} not found")

        # A plan change goes through change_plan so history is always written.
        new_plan_id = changes.pop("plan_id", None)
        if new_plan_id is not None:
            self.change_plan(subscriber_id, new_plan_id, current_user)
        if changes:
            self.subscribers.update(subscriber, changes)
        return subscriber

    def delete(self, subscriber_id: int, current_user: User) -> Subscriber:
        if self._is_customer(current_user):
            self.get(subscriber_id, current_user)
            raise ForbiddenError("Only staff or admin can delete subscribers")

        subscriber = self.get(subscriber_id, current_user)

        if subscriber.status == "ported_out":
            return subscriber

        return self.subscribers.update(subscriber, {"status": "inactive"})