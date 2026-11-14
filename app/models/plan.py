# app/models/plan.py
# Job of this file: describe the "plans" table (prepaid packs we sell).

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Plan(Base):
    # The real table name in the database.
    __tablename__ = "plans"

    # CheckConstraints are rules the DATABASE checks before saving a row.
    # If a rule is broken, the database refuses to save it.
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_plans_price_non_negative"),
        CheckConstraint("validity_days > 0", name="ck_plans_validity_positive"),
        CheckConstraint("data_mb_per_day >= 0", name="ck_plans_data_non_negative"),
    )

    # Automatic unique number for each plan.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Plan name, for example "Super 299". Required.
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Numeric(10, 2) = exact money value, like 299.00 (never use Float for money).
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # How many days the plan lasts. Must be greater than 0.
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # Data allowed per day, always stored in MB (so 1.5 GB is saved as 1536).
    data_mb_per_day: Mapped[int] = mapped_column(Integer, nullable=False)

    # "int | None" means this column is allowed to be empty (nullable).
    # Some plans are data-only, so they have no voice minutes or SMS.
    voice_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # A plan can be switched off (is_active=False) without deleting it.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # The database fills in the current time by itself.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    