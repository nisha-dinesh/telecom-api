# app/schemas/usage_record.py
# Job of this file: define the shape of usage data going IN and OUT.
# Security/accuracy rule: the client sends raw_value + unit only.
# The service calculates data_mb, so the numbers can never disagree.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The only 2 units allowed (same as the database CheckConstraint).
UsageUnit = Literal["MB", "GB"]


class UsageCreate(BaseModel):
    """What the client sends to log data usage. NO data_mb here on purpose."""

    subscriber_id: int = Field(gt=0)
    usage_date: datetime
    # gt=0 -> must be more than 0. le=1_000_000 -> blocks absurd numbers.
    raw_value: float = Field(gt=0, le=1_000_000, examples=[1.5])
    unit: UsageUnit = Field(examples=["GB"])


class UsageRead(BaseModel):
    """What we send back. data_mb is the converted value (1 GB = 1024 MB)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    usage_date: datetime
    raw_value: float
    unit: str
    data_mb: float


class UsageSummary(BaseModel):
    """Total usage of one subscriber, always in MB so rows can be added fairly."""

    subscriber_id: int
    total_mb: float
    record_count: int