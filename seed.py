# seed.py
# Job of this file: fill the database with demo data, including MESSY cases:
#   1. a ported_out subscriber who still has a plan, recharges and recent usage
#   2. duplicate complaints (app + call centre) linked to the original
#   3. usage stored in mixed MB and GB (data_mb is the converted value)
# Run it once:  python seed.py      (delete telecom.db first to seed again)

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

import app.models  # noqa: F401  (registers all tables)
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.circle import Circle
from app.models.complaint import Complaint
from app.models.plan import Plan
from app.models.plan_change import PlanChange
from app.models.recharge import Recharge
from app.models.subscriber import Subscriber
from app.models.usage_record import UsageRecord
from app.models.user import User
from app.services.complaint_service import make_dedupe_key
from app.services.usage_service import to_mb

# Naive UTC "now", the same way the database stores times.
NOW = datetime.now(timezone.utc).replace(tzinfo=None)


def days_ago(days: int) -> datetime:
    return NOW - timedelta(days=days)


def count(db, model, *conditions) -> int:
    query = select(func.count()).select_from(model)
    for condition in conditions:
        query = query.where(condition)
    return db.scalar(query) or 0


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if count(db, User):
        print("Database already has data. Stop the server, delete telecom.db and run again.")
        return

    # ---------- users (demo passwords only, never use these in real life) ----------
    def make_user(email: str, password: str, role: str) -> User:
        user = User(email=email, hashed_password=hash_password(password), role=role)
        db.add(user)
        return user

    admin = make_user("admin@example.com", "Admin@12345", "admin")
    staff = make_user("staff@example.com", "Staff@12345", "staff")
    riya = make_user("riya@example.com", "Riya@12345", "user")
    amit = make_user("amit@example.com", "Amit@12345", "user")
    neha = make_user("neha@example.com", "Neha@12345", "user")

    # ---------- circles ----------
    gujarat, delhi, maharashtra = (Circle(name=n) for n in ("Gujarat", "Delhi", "Maharashtra"))
    db.add_all([gujarat, delhi, maharashtra])

    # ---------- plans (data is always stored in MB per day: 1.5 GB = 1536) ----------
    booster = Plan(name="Data Booster 99", price=99, validity_days=14, data_mb_per_day=512)
    basic = Plan(name="Basic 199", price=199, validity_days=28, data_mb_per_day=1024, voice_minutes=300, sms=100)
    super299 = Plan(name="Super 299", price=299, validity_days=28, data_mb_per_day=1536, voice_minutes=1000, sms=300)
    mega = Plan(name="Mega 599", price=599, validity_days=84, data_mb_per_day=2048, voice_minutes=3000, sms=900)
    legacy = Plan(name="Legacy 149", price=149, validity_days=28, data_mb_per_day=1024, is_active=False)
    db.add_all([booster, basic, super299, mega, legacy])
    db.flush()  # gives every row its id

    # ---------- subscribers ----------
    def make_sub(user, msisdn, name, circle, plan, status) -> Subscriber:
        sub = Subscriber(
            user_id=user.id, msisdn=msisdn, name=name, circle_id=circle.id,
            plan_id=plan.id if plan else None, status=status,
        )
        db.add(sub)
        return sub

    s_riya = make_sub(riya, "9876543210", "Riya Patel", gujarat, super299, "active")
    s_amit = make_sub(amit, "9123456780", "Amit Shah", delhi, basic, "active")
    s_neha = make_sub(neha, "9898989898", "Neha Joshi", gujarat, mega, "active")
    # MESSY: ported out, but still has a plan, recharges and usage below.
    s_karan = make_sub(amit, "9712345678", "Karan Mehta", maharashtra, super299, "ported_out")
    s_meera = make_sub(neha, "9825012345", "Meera Desai", gujarat, None, "inactive")
    db.flush()

    # ---------- plan history ----------
    for sub, old, new in [
        (s_riya, None, basic), (s_riya, basic, super299), (s_amit, None, basic),
        (s_neha, None, mega), (s_karan, None, super299),
    ]:
        db.add(PlanChange(subscriber_id=sub.id, old_plan_id=old.id if old else None,
                          new_plan_id=new.id, changed_at=days_ago(30)))

    # ---------- recharges (amount = the plan's price at that time) ----------
    def make_recharge(sub, plan, status, reference, ago):
        db.add(Recharge(subscriber_id=sub.id, plan_id=plan.id, amount=plan.price,
                        status=status, payment_reference=reference, created_at=days_ago(ago)))

    make_recharge(s_riya, super299, "successful", "PAY1001", 20)
    make_recharge(s_riya, super299, "successful", "PAY1002", 2)
    make_recharge(s_amit, basic, "successful", "PAY1003", 10)
    make_recharge(s_amit, basic, "failed", None, 1)
    make_recharge(s_neha, mega, "successful", "PAY1004", 5)
    # MESSY: the ported-out number still recharged recently.
    make_recharge(s_karan, super299, "successful", "PAY1005", 3)
    make_recharge(s_karan, super299, "pending", None, 1)

    # ---------- usage (MESSY: some rows sent in MB, some in GB) ----------
    def make_usage(sub, raw_value, unit, ago):
        db.add(UsageRecord(subscriber_id=sub.id, usage_date=days_ago(ago), raw_value=raw_value,
                           unit=unit, data_mb=to_mb(raw_value, unit)))

    make_usage(s_riya, 500, "MB", 3)
    make_usage(s_riya, 1.5, "GB", 2)
    make_usage(s_riya, 800, "MB", 1)
    make_usage(s_amit, 2, "GB", 4)
    make_usage(s_amit, 300, "MB", 1)
    make_usage(s_neha, 3.2, "GB", 3)
    make_usage(s_neha, 900, "MB", 1)
    # MESSY: usage keeps arriving for the ported-out number.
    make_usage(s_karan, 600, "MB", 2)
    make_usage(s_karan, 1.2, "GB", 1)

    # ---------- complaints (MESSY: duplicates from app and call centre) ----------
    def make_complaint(sub, channel, category, text, status, original=None) -> Complaint:
        complaint = Complaint(
            subscriber_id=sub.id, channel=channel, category=category, description=text,
            status=status, dedupe_key=make_dedupe_key(sub.id, category),
            linked_to_id=original.id if original else None,  # a copy points to the original
        )
        db.add(complaint)
        db.flush()  # so the next complaint can link to this id
        return complaint

    c1 = make_complaint(s_riya, "app", "network", "No signal since morning", "open")
    make_complaint(s_riya, "call_centre", "network", "Customer reports no network", "open", c1)
    c2 = make_complaint(s_amit, "app", "billing", "Charged twice for one recharge", "resolved")
    make_complaint(s_amit, "call_centre", "billing", "Double charge on recharge", "resolved", c2)
    make_complaint(s_amit, "app", "billing", "Still not refunded", "open", c2)
    make_complaint(s_neha, "call_centre", "plan", "Wants to compare plans", "in_progress")
    make_complaint(s_karan, "app", "recharge_failed", "Recharge not reflecting", "open")

    db.commit()

    # ---------- summary ----------
    print(
        f"Seeded: users={count(db, User)} circles={count(db, Circle)} plans={count(db, Plan)} "
        f"subscribers={count(db, Subscriber)} recharges={count(db, Recharge)} "
        f"usage_records={count(db, UsageRecord)} complaints={count(db, Complaint)} "
        f"plan_changes={count(db, PlanChange)}"
    )
    print(
        "Messy cases: "
        f"ported_out_with_plan={count(db, Subscriber, Subscriber.status == 'ported_out', Subscriber.plan_id.is_not(None))} "
        f"duplicate_complaints={count(db, Complaint, Complaint.linked_to_id.is_not(None))} "
        f"usage_rows_in_GB={count(db, UsageRecord, UsageRecord.unit == 'GB')}"
    )
    print("Logins (demo only): admin@example.com / Admin@12345, staff@example.com / Staff@12345,")
    print("                    riya@example.com / Riya@12345, amit@example.com / Amit@12345, neha@example.com / Neha@12345")
    db.close()


if __name__ == "__main__":
    main()