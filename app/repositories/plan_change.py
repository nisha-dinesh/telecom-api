# app/repositories/plan_change.py
# Job of this file: database access for plan-change history.
# History is only ever ADDED (by the service), never edited or deleted.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan_change import PlanChange
from app.repositories.base import BaseRepository


class PlanChangeRepository(BaseRepository[PlanChange]):
    def __init__(self, db: Session):
        super().__init__(db, PlanChange)

    def list_for_subscriber(self, subscriber_id: int) -> list[PlanChange]:
        """All plan changes of one subscriber, newest first."""
        rows = self.db.scalars(
            select(PlanChange)
            .where(PlanChange.subscriber_id == subscriber_id)
            .order_by(PlanChange.id.desc())
        ).all()
        return list(rows)