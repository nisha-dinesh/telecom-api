# app/models/recharge.py
# Job of this file: describe the "recharges" table (each payment for a plan).

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Recharge(Base):
    # The real table name in the database.
    __tablename__ = "recharges"

    # Database rules: money can't be negative, and status must be one of 3 words.
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_recharges_amount_non_negative"),
        CheckConstraint(
            "status IN ('pending', 'successful', 'failed')",
            name="ck_recharges_status_valid",
        ),
    )

    # Automatic unique number for each recharge.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Who recharged. Must be the id of a real subscriber.
    # index=True -> fast search for "all recharges of this subscriber".
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)

    # Which plan they bought. Must be the id of a real plan.
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))

    # The money actually paid. We copy it here so that if the plan's price
    # changes later, old recharges still show what the customer really paid.
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # pending / successful / failed.
    status: Mapped[str] = mapped_column(String, nullable=False)

    # Payment gateway reference. Can be empty (nullable) for pending/failed payments.
    payment_reference: Mapped[str | None] = mapped_column(String, nullable=True)

    # The database fills in the current time by itself.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())