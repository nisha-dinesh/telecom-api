# app/schemas/subscriber.py
# Job of this file: define the shape of subscriber data going IN and OUT,
# and check that the mobile number (msisdn) looks like a real Indian mobile number.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The only 3 words allowed for status (same as the database CheckConstraint).
SubscriberStatus = Literal["active", "inactive", "ported_out"]

# Regex = a pattern the text must match:
#   ^      start of text
#   [6-9]  first digit must be 6, 7, 8 or 9
#   \d{9}  then exactly 9 more digits (so 10 digits in total)
#   $      end of text
MSISDN_PATTERN = r"^[6-9]\d{9}$"


class SubscriberCreate(BaseModel):
    """What the client sends to add a subscriber.
    No 'status' here: a new subscriber always starts as 'active' (set by the service)."""

    msisdn: str = Field(pattern=MSISDN_PATTERN, examples=["9876543210"])
    name: str = Field(min_length=2, max_length=100, examples=["Riya Patel"])
    circle_id: int = Field(gt=0)
    plan_id: int | None = Field(default=None, gt=0)

    # Only staff/admin may use this. For an end user, the service ignores it and
    # uses the id of the logged-in user from the JWT instead.
    user_id: int | None = Field(default=None, gt=0)


class SubscriberUpdate(BaseModel):
    """Staff/admin changes a subscriber. Every field is optional.
    msisdn is NOT here: a phone number should never be edited."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    circle_id: int | None = Field(default=None, gt=0)
    plan_id: int | None = Field(default=None, gt=0)
    status: SubscriberStatus | None = None


class SubscriberRead(BaseModel):
    """What we send back to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    msisdn: str
    name: str
    circle_id: int
    plan_id: int | None
    status: str
    created_at: datetime
    