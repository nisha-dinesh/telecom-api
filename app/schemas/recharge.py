# app/schemas/recharge.py
# Job of this file: define the shape of recharge data going IN and OUT.
# Security rule: the client NEVER sends the amount. The service copies the
# real price from the plan, so nobody can pay 1 rupee for a 599 plan.

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The only 3 words allowed for status (same as the database CheckConstraint).
RechargeStatus = Literal["pending", "successful", "failed"]


class RechargeCreate(BaseModel):
    """What the client sends to recharge: only WHO and WHICH PLAN.
    No amount, no status, no payment_reference: the server decides those."""

    subscriber_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)


class RechargeStatusUpdate(BaseModel):
    """Staff (or the payment system) updates the result of a recharge."""

    status: RechargeStatus
    # Optional: the payment gateway's reference number, e.g. "PAY123456".
    payment_reference: str | None = Field(default=None, max_length=100)


class RechargeRead(BaseModel):
    """What we send back to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    plan_id: int
    amount: Decimal
    status: str
    payment_reference: str | None
    created_at: datetime