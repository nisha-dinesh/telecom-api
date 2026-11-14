# app/schemas/plan.py
# Job of this file: define the shape of plan data going IN and OUT of the API,
# and enforce the validation rules (no negative price, etc.).

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanCreate(BaseModel):
    """What the client sends to create a plan."""

    name: str = Field(min_length=2, max_length=100, examples=["Super 299"])

    # ge = "greater than or equal to", gt = "greater than".
    # max_digits/decimal_places match the database column Numeric(10, 2).
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2, examples=["299.00"])
    validity_days: int = Field(gt=0, examples=[28])
    data_mb_per_day: int = Field(ge=0, examples=[1536])

    # "int | None = None" -> optional field. If missing, it is None (empty).
    voice_minutes: int | None = Field(default=None, ge=0)
    sms: int | None = Field(default=None, ge=0)


class PlanUpdate(BaseModel):
    """What the client sends to change a plan. Every field is optional,
    so the client sends only what they want to change."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    validity_days: int | None = Field(default=None, gt=0)
    data_mb_per_day: int | None = Field(default=None, ge=0)
    voice_minutes: int | None = Field(default=None, ge=0)
    sms: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class PlanRead(BaseModel):
    """What we send back to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    validity_days: int
    data_mb_per_day: int
    voice_minutes: int | None
    sms: int | None
    is_active: bool
    created_at: datetime