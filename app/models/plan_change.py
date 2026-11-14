# app/models/plan_change.py
# Job of this file: describe the "plan_changes" table (history of plan switches).

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlanChange(Base):
    # The real table name in the database.
    __tablename__ = "plan_changes"

    # Automatic unique number for each change.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Who changed their plan. Must be the id of a real subscriber.
    # index=True -> fast search for "plan history of this subscriber".
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)

    # The plan they HAD before. "int | None" = nullable, because a subscriber
    # who had no plan yet has no old plan when choosing their first one.
    old_plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)

    # The plan they MOVED TO. Required.
    # (Both old_plan_id and new_plan_id point to the same "plans" table.)
    new_plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)

    # The database fills in the time of the change by itself.
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())