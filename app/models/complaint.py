# app/models/complaint.py
# Job of this file: describe the "complaints" table (customer problems).

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Complaint(Base):
    # The real table name in the database.
    __tablename__ = "complaints"

    # Database rules: channel and status can only be one of these words.
    __table_args__ = (
        CheckConstraint(
            "channel IN ('app', 'call_centre')",
            name="ck_complaints_channel_valid",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="ck_complaints_status_valid",
        ),
    )

    # Automatic unique number for each complaint.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Who complained. Must be the id of a real subscriber.
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)

    # Where the complaint came from: "app" or "call_centre".
    channel: Mapped[str] = mapped_column(String, nullable=False)

    # Type of problem, e.g. "network", "billing", "recharge_failed".
    category: Mapped[str] = mapped_column(String, nullable=False)

    # Text = long writing (the customer's full explanation).
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # open / in_progress / resolved / closed.
    status: Mapped[str] = mapped_column(String, nullable=False)

    # A "fingerprint" of the complaint (the service layer will build it).
    # Two complaints about the same problem get the same key, so duplicates
    # are easy to find. index=True -> fast search by this key.
    dedupe_key: Mapped[str | None] = mapped_column(String, index=True, nullable=True)

    # SELF-REFERENCING foreign key: points to another row in the SAME table.
    # If this complaint is a duplicate, this holds the id of the ORIGINAL one.
    # It is empty (None) for original complaints.
    linked_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("complaints.id"), nullable=True
    )

    # The database fills in the current time by itself.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())