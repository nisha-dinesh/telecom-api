# app/schemas/plan_change.py
# Job of this file: shapes for plan-change history.
# There is NO "create" schema on purpose: history is written only by the
# service when a plan really changes, so nobody can fake it.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChangePlanRequest(BaseModel):
    """What the client sends to switch a subscriber to a new plan.
    The service finds the old plan by itself and writes the history row."""

    new_plan_id: int = Field(gt=0)


class PlanChangeRead(BaseModel):
    """What we send back when showing plan history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    old_plan_id: int | None  # None = subscriber had no plan before
    new_plan_id: int
    changed_at: datetime