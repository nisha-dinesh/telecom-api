# app/services/recharge_service.py
# Job of this file: business rules for recharges (payments).
# current_user is the logged-in User object (the router will pass it in).

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    ForbiddenError,
    NotFoundError,
)
from app.models.plan_change import PlanChange
from app.models.recharge import Recharge
from app.models.user import User
from app.repositories.plan import PlanRepository
from app.repositories.plan_change import PlanChangeRepository
from app.repositories.recharge import RechargeRepository
from app.repositories.subscriber import SubscriberRepository
from app.schemas.recharge import RechargeCreate, RechargeStatusUpdate


class RechargeService:
    def __init__(self, db: Session):
        self.recharges = RechargeRepository(db)
        self.subscribers = SubscriberRepository(db)
        self.plans = PlanRepository(db)
        self.changes = PlanChangeRepository(db)

    @staticmethod
    def _is_customer(user: User) -> bool:
        """role 'user' = an end customer. 'staff' and 'admin' are employees."""
        return user.role == "user"

    # ---------- read ----------

    def get(self, recharge_id: int, current_user: User) -> Recharge:
        recharge = self.recharges.get(recharge_id)
        if recharge is None:
            raise NotFoundError(f"Recharge {recharge_id} not found")
        if self._is_customer(current_user):
            # A customer may only see recharges of their OWN numbers.
            subscriber = self.subscribers.get(recharge.subscriber_id)
            if subscriber is None or subscriber.user_id != current_user.id:
                raise NotFoundError(f"Recharge {recharge_id} not found")  # BOLA
        return recharge

    def list(
        self,
        offset: int,
        limit: int,
        current_user: User,
        subscriber_id: int | None = None,
        plan_id: int | None = None,
        status: str | None = None,
    ) -> "tuple[list[Recharge], int]":
        # Security filter: a customer's list is ALWAYS limited to their own numbers.
        owner_id = current_user.id if self._is_customer(current_user) else None
        filters = RechargeRepository.build_filters(
            subscriber_id=subscriber_id,
            plan_id=plan_id,
            status=status,
            owner_user_id=owner_id,
        )
        return self.recharges.get_many(offset=offset, limit=limit, filters=filters)

    # ---------- write ----------

    def create(self, data: RechargeCreate, current_user: User) -> Recharge:
        subscriber = self.subscribers.get(data.subscriber_id)
        # A customer cannot even learn that someone else's number exists.
        if subscriber is None or (
            self._is_customer(current_user) and subscriber.user_id != current_user.id
        ):
            raise NotFoundError(f"Subscriber {data.subscriber_id} not found")

        # Rule: only active numbers can recharge (not inactive, not ported out).
        if subscriber.status != "active":
            raise BusinessRuleError(
                f"A {subscriber.status} number cannot be recharged"
            )

        plan = self.plans.get(data.plan_id)
        if plan is None:
            raise NotFoundError(f"Plan {data.plan_id} not found")
        if not plan.is_active:
            raise BusinessRuleError(f"Plan {data.plan_id} is not active")

        return self.recharges.add(
            Recharge(
                subscriber_id=subscriber.id,
                plan_id=plan.id,
                amount=plan.price,  # the price comes from the plan, never from the client
                status="pending",  # the client cannot choose this
            )
        )

    def update_status(
        self, recharge_id: int, data: RechargeStatusUpdate, current_user: User
    ) -> Recharge:
        """Staff/admin record the payment result."""
        if self._is_customer(current_user):
            raise ForbiddenError("Only staff or admin can update a recharge")
        recharge = self.get(recharge_id, current_user)

        # A finished payment is locked, so payment history can't be rewritten.
        if recharge.status != "pending":
            raise BusinessRuleError(
                f"A {recharge.status} recharge cannot be changed"
            )
        if data.status == "pending":
            raise BusinessRuleError("Status must change to successful or failed")

        changes = {"status": data.status}
        if data.payment_reference is not None:
            changes["payment_reference"] = data.payment_reference
        recharge = self.recharges.update(recharge, changes)

        # A successful payment puts the bought plan on the number.
        if data.status == "successful":
            self._activate_plan(recharge)
        return recharge

    def _activate_plan(self, recharge: Recharge) -> None:
        subscriber = self.subscribers.get(recharge.subscriber_id)
        if (
            subscriber is not None
            and subscriber.status == "active"
            and subscriber.plan_id != recharge.plan_id
        ):
            old_plan_id = subscriber.plan_id
            self.subscribers.update(subscriber, {"plan_id": recharge.plan_id})
            self.changes.add(
                PlanChange(
                    subscriber_id=subscriber.id,
                    old_plan_id=old_plan_id,
                    new_plan_id=recharge.plan_id,
                )
            )