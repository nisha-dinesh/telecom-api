# app/models/usage_record.py
# Job of this file: describe the "usage_records" table (data used per day).

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UsageRecord(Base):
    # The real table name in the database.
    __tablename__ = "usage_records"

    # Database rules:
    #  - raw_value must be more than 0
    #  - unit must be exactly "MB" or "GB"
    #  - data_mb (the converted value) can never be negative
    __table_args__ = (
        CheckConstraint("raw_value > 0", name="ck_usage_raw_value_positive"),
        CheckConstraint("unit IN ('MB', 'GB')", name="ck_usage_unit_valid"),
        CheckConstraint("data_mb >= 0", name="ck_usage_data_mb_non_negative"),
    )

    # Automatic unique number for each usage record.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Whose usage this is. Must be the id of a real subscriber.
    # index=True -> fast search for "all usage of this subscriber".
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)

    # The day the data was used. Required.
    usage_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # EXACTLY what the source system sent, e.g. 1.5 with unit "GB".
    # We keep it so the original value is never lost.
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)

    # The same amount converted to MB (1 GB = 1024 MB), so rows can be
    # added up and compared fairly. The service layer will calculate this.
    data_mb: Mapped[float] = mapped_column(Float, nullable=False)