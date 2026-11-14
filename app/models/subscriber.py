# app/models/subscriber.py
# Job of this file: describe the "subscribers" table (one mobile number per row).

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Subscriber(Base):
    # The real table name in the database.
    __tablename__ = "subscribers"

    # Database rule: status can only be one of these three words.
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'ported_out')",
            name="ck_subscribers_status_valid",
        ),
    )

    # Automatic unique number for each subscriber.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ForeignKey("users.id") = this must be the id of a real row in "users".
    # It links the subscriber to the login account that owns this number.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # The mobile number (MSISDN), for example "9876543210".
    # unique=True -> one number can only exist once. index=True -> fast search.
    msisdn: Mapped[str] = mapped_column(String(15), unique=True, nullable=False, index=True)

    # The customer's name. Required.
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Which telecom region (circle) this number belongs to.
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"))

    # "int | None" -> nullable. A new subscriber may not have a plan yet.
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)

    # The ONE trusted field for the number's state: active / inactive / ported_out.
    status: Mapped[str] = mapped_column(String, nullable=False)

    # The database fills in the current time by itself.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())