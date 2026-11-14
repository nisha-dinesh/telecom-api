# app/services/admin_service.py
# Job of this file: admin clean-up of messy data.

from sqlalchemy.orm import Session

from app.repositories.recharge import RechargeRepository
from app.repositories.subscriber import SubscriberRepository


class AdminService:
    def __init__(self, db: Session):
        self.subscribers = SubscriberRepository(db)
        self.recharges = RechargeRepository(db)

    def fix_ported_out(self) -> dict:
        """Ported-out numbers must not look active:
        - clear the plan they still hold
        - mark their pending recharges as failed
        Safe to run twice: the second run changes nothing."""
        fixed = 0
        failed_recharges = 0
        filters = SubscriberRepository.build_filters(status="ported_out")
        page = 0
        while True:
            rows, _ = self.subscribers.get_many(offset=page * 100, limit=100, filters=filters)
            if not rows:
                break
            for subscriber in rows:
                if subscriber.plan_id is not None:
                    self.subscribers.update(subscriber, {"plan_id": None})
                    fixed += 1
                pending, _ = self.recharges.get_many(
                    offset=0,
                    limit=1000,
                    filters=RechargeRepository.build_filters(
                        subscriber_id=subscriber.id, status="pending"
                    ),
                )
                for recharge in pending:
                    self.recharges.update(recharge, {"status": "failed"})
                    failed_recharges += 1
            page += 1
        return {"fixed": fixed, "pending_recharges_failed": failed_recharges}