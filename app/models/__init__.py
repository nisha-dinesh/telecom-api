# app/models/__init__.py
# Job of this file: import EVERY model in one place.
# SQLAlchemy only creates tables for models that have been imported,
# so main.py just does "import app.models" and all 8 tables are registered.

# "noqa: F401" tells VS Code: "yes, these imports look unused, but that is on purpose".
from app.models.circle import Circle  # noqa: F401
from app.models.complaint import Complaint  # noqa: F401
from app.models.plan import Plan  # noqa: F401
from app.models.plan_change import PlanChange  # noqa: F401
from app.models.recharge import Recharge  # noqa: F401
from app.models.subscriber import Subscriber  # noqa: F401
from app.models.usage_record import UsageRecord  # noqa: F401
from app.models.user import User  # noqa: F401
