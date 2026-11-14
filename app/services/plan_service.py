# app/services/plan_service.py
# Job of this file: business rules for plans (create, update, search, delete).

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.plan import Plan
from app.models.plan_change import PlanChange
from app.repositories.plan import PlanRepository
from app.repositories.plan_change import PlanChangeRepository
from app.repositories.recharge import RechargeRepository
from app.repositories.subscriber import SubscriberRepository
from app.schemas.plan import PlanCreate, PlanUpdate


class PlanService:
    def __init__(self, db: Session):
        self.plans = PlanRepository(db)
        self.subscribers = SubscriberRepository(db)
        self.recharges = RechargeRepository(db)
        self.changes = PlanChangeRepository(db)

    def create(self, data: PlanCreate) -> Plan:
        return self.plans.add(Plan(**data.model_dump()))

    def get(self, plan_id: int) -> Plan:
        plan = self.plans.get(plan_id)
        if plan is None:
            raise NotFoundError(f"Plan {plan_id} not found")
        return plan

    def list(
        self,
        offset: int,
        limit: int,
        search: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        min_data_mb: int | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Plan], int]:
        filters = PlanRepository.build_filters(
            search, min_price, max_price, min_data_mb, is_active
        )
        return self.plans.get_many(offset=offset, limit=limit, filters=filters)

    def update(self, plan_id: int, data: PlanUpdate) -> Plan:
        plan = self.get(plan_id)
        # exclude_unset = only the fields the client really sent.
        return self.plans.update(plan, data.model_dump(exclude_unset=True))

    def _is_used(self, plan_id: int) -> bool:
        """True if any subscriber, recharge or plan-change history points to this plan."""
        checks = [
            (self.subscribers, SubscriberRepository.build_filters(plan_id=plan_id)),
            (self.recharges, RechargeRepository.build_filters(plan_id=plan_id)),
            (
                self.changes,
                [or_(PlanChange.old_plan_id == plan_id, PlanChange.new_plan_id == plan_id)],
            ),
        ]
        for repo, filters in checks:
            _, total = repo.get_many(offset=0, limit=1, filters=filters)
            if total:
                return True
        return False

    def delete(self, plan_id: int) -> str:
        """Delete an unused plan; deactivate a used one. Returns 'deleted' or 'deactivated'."""
        plan = self.get(plan_id)
        if self._is_used(plan_id):
            self.plans.update(plan, {"is_active": False})
            return "deactivated"
        self.plans.delete(plan)
        return "deleted"