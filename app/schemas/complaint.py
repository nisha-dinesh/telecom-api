# app/schemas/complaint.py
# Job of this file: define the shape of complaint data going IN and OUT.
# Rule: the client writes the problem; the SERVER controls status on create,
# dedupe_key and linked_to_id (duplicate detection happens in the service).

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Same words as the database CheckConstraints.
ComplaintChannel = Literal["app", "call_centre"]
ComplaintStatus = Literal["open", "in_progress", "resolved", "closed"]

# A FIXED list of categories, so "Network" / "network " / "NETWORK" can never
# create different fingerprints for the same problem. Add more words later if needed.
ComplaintCategory = Literal[
    "network", "billing", "recharge_failed", "plan", "sim", "other"
]


class ComplaintCreate(BaseModel):
    """What the client sends to raise a complaint.
    No status / dedupe_key / linked_to_id: the service sets those."""

    subscriber_id: int = Field(gt=0)
    channel: ComplaintChannel = Field(examples=["app"])
    category: ComplaintCategory = Field(examples=["network"])
    description: str = Field(min_length=5, max_length=2000)


class ComplaintUpdate(BaseModel):
    """Staff changes the status of a complaint (open -> in_progress -> resolved...)."""

    status: ComplaintStatus


class ComplaintRead(BaseModel):
    """What we send back. dedupe_key and linked_to_id are visible so staff
    can see which complaints are duplicates of which."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    channel: str
    category: str
    description: str
    status: str
    dedupe_key: str | None
    linked_to_id: int | None
    created_at: datetime