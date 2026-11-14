# tests/test_api.py
# Job of this file: API tests. They call the real endpoints like a browser would
# and check the status codes and the security rules (roles, ownership, prices).

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from tests.conftest import PASSWORD  # noqa: F401  (pythonpath=. makes this import work)


def iso_ago(days: float, aware: bool = False) -> str:
    """A date/time `days` ago (negative = in the future), as text."""
    value = datetime.now(timezone.utc) - timedelta(days=days)
    return (value if aware else value.replace(tzinfo=None)).isoformat()


def make_sub(client, headers, catalog, msisdn="9876543210", name="Riya Patel", plan="basic", **extra):
    body = {
        "msisdn": msisdn,
        "name": name,
        "circle_id": catalog["circle"],
        "plan_id": catalog[plan] if plan else None,
        **extra,
    }
    return client.post("/subscribers", json=body, headers=headers)


# ---------------------------------------------------------------- auth & users


def test_register_login_me(client):
    r = client.post("/auth/register", json={"email": "Riya@Example.com", "password": "secret123", "role": "admin"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "riya@example.com"  # saved in lowercase
    assert body["role"] == "user"  # the extra "role" field was ignored
    assert "hashed_password" not in body
    r = client.post("/auth/register", json={"email": "RIYA@example.com", "password": "secret123"})
    assert r.status_code == 409
    r = client.post("/auth/login", json={"email": "RIYA@example.com", "password": "secret123"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    headers = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert client.get("/auth/me", headers=headers).json()["email"] == "riya@example.com"


def test_login_failures_look_identical(client, make_user):
    make_user("riya@example.com")
    make_user("gone@example.com", is_active=False)
    wrong = client.post("/auth/login", json={"email": "riya@example.com", "password": "wrongpass1"})
    unknown = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrongpass1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # attackers can't tell which emails exist
    disabled = client.post("/auth/login", json={"email": "gone@example.com", "password": PASSWORD})
    assert disabled.status_code == 401
    assert disabled.json()["error"]["message"] == "This account is disabled"


def test_token_problems_are_rejected(client, customer, make_user):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401

    def token_with(**payload):
        return {"Authorization": "Bearer " + jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)}

    soon = datetime.now(timezone.utc) + timedelta(minutes=5)
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert client.get("/auth/me", headers=token_with(sub=str(customer.id), exp=past)).status_code == 401
    assert client.get("/auth/me", headers=token_with(sub="abc", exp=soon)).status_code == 401
    assert client.get("/auth/me", headers=token_with(sub="9999", exp=soon)).status_code == 401
    gone = make_user("gone@example.com", is_active=False)
    assert client.get("/auth/me", headers=token_with(sub=str(gone.id), exp=soon)).status_code == 401
    assert client.get("/auth/me", headers=token_with(sub=str(customer.id), exp=soon)).status_code == 200


def test_user_management_is_admin_only(client, auth, admin, staff, customer):
    assert client.get("/users", headers=auth(customer)).status_code == 403
    assert client.get("/users", headers=auth(staff)).status_code == 403
    r = client.get("/users", headers=auth(admin))
    assert r.status_code == 200 and r.json()["total"] == 3

    r = client.post("/users", json={"email": "new@example.com", "password": "newpass123", "role": "staff"}, headers=auth(admin))
    assert r.status_code == 201 and r.json()["role"] == "staff"
    new_id = r.json()["id"]
    r = client.post("/users", json={"email": "new@example.com", "password": "newpass123"}, headers=auth(admin))
    assert r.status_code == 409

    assert client.get(f"/users/{new_id}", headers=auth(admin)).status_code == 200
    assert client.get("/users/9999", headers=auth(admin)).status_code == 404
    r = client.patch(f"/users/{new_id}", json={"role": "user", "is_active": False}, headers=auth(admin))
    assert r.status_code == 200 and r.json()["role"] == "user" and r.json()["is_active"] is False

    # An admin must not lock themselves out.
    assert client.patch(f"/users/{admin.id}", json={"role": "staff"}, headers=auth(admin)).status_code == 422
    assert client.patch(f"/users/{admin.id}", json={"is_active": False}, headers=auth(admin)).status_code == 422


# ------------------------------------------------------------ circles & plans


def test_circles_crud_and_rules(client, auth, staff, customer, catalog):
    s, c = auth(staff), auth(customer)
    assert client.post("/circles", json={"name": "Delhi"}, headers=c).status_code == 403
    r = client.post("/circles", json={"name": "Delhi"}, headers=s)
    assert r.status_code == 201
    delhi = r.json()["id"]
    assert client.post("/circles", json={"name": "Delhi"}, headers=s).status_code == 409
    assert client.get("/circles", headers=c).json()["total"] == 2
    assert client.get(f"/circles/{delhi}", headers=c).json()["name"] == "Delhi"
    assert client.get("/circles/9999", headers=c).status_code == 404
    assert client.put(f"/circles/{delhi}", json={"name": "Gujarat"}, headers=s).status_code == 409
    assert client.put(f"/circles/{delhi}", json={"name": "Delhi"}, headers=s).status_code == 200  # own name
    assert client.put(f"/circles/{delhi}", json={"name": "New Delhi"}, headers=s).json()["name"] == "New Delhi"
    assert client.delete(f"/circles/{delhi}", headers=s).status_code == 204
    assert client.get(f"/circles/{delhi}", headers=c).status_code == 404


def test_plans_crud_search_filter_pagination(client, auth, admin, staff, customer):
    s, c, a = auth(staff), auth(customer), auth(admin)
    basic = {"name": "Basic 199", "price": 199, "validity_days": 28, "data_mb_per_day": 1024}
    mega = {"name": "Mega 599", "price": 599, "validity_days": 84, "data_mb_per_day": 2048}
    r = client.post("/plans", json=basic, headers=s)
    assert r.status_code == 201
    basic_id = r.json()["id"]
    client.post("/plans", json=mega, headers=s)

    assert client.post("/plans", json=basic, headers=c).status_code == 403
    assert client.post("/plans", json={**basic, "price": -5}, headers=s).status_code == 422
    assert client.post("/plans", json={**basic, "validity_days": 0}, headers=s).status_code == 422
    r = client.post("/plans", json={"name": "x"}, headers=s)
    assert r.status_code == 422 and r.json()["error"]["details"]

    assert client.get("/plans", headers=c).json()["total"] == 2
    page = client.get("/plans?page=2&page_size=1", headers=c).json()
    assert len(page["items"]) == 1 and page["items"][0]["name"] == "Mega 599" and page["total"] == 2
    assert client.get("/plans?min_price=300", headers=c).json()["items"][0]["name"] == "Mega 599"
    assert client.get("/plans?max_price=300", headers=c).json()["items"][0]["name"] == "Basic 199"
    assert client.get("/plans?min_data_mb=2000", headers=c).json()["total"] == 1
    assert client.get("/plans?search=mega", headers=c).json()["total"] == 1
    assert client.get("/plans?is_active=false", headers=c).json()["total"] == 0
    assert client.get("/plans?page_size=500", headers=c).status_code == 422
    assert client.get("/plans?page=0", headers=c).status_code == 422
    assert client.get("/plans").status_code == 401

    assert client.get(f"/plans/{basic_id}", headers=c).status_code == 200
    assert client.get("/plans/9999", headers=c).status_code == 404
    assert client.patch(f"/plans/{basic_id}", json={"price": 249}, headers=c).status_code == 403
    r = client.patch(f"/plans/{basic_id}", json={"price": 249, "is_active": False}, headers=s)
    assert float(r.json()["price"]) == 249.0 and r.json()["is_active"] is False

    assert client.delete(f"/plans/{basic_id}", headers=s).status_code == 403  # admin only
    assert client.delete(f"/plans/{basic_id}", headers=a).json() == {"result": "deleted"}
    assert client.get(f"/plans/{basic_id}", headers=c).status_code == 404


# ---------------------------------------------------------------- subscribers


def test_subscriber_rules(client, auth, customer, other, staff, catalog):
    c, o, s = auth(customer), auth(other), auth(staff)

    # The customer tries to create a number under someone else's account: ignored.
    r = make_sub(client, c, catalog, user_id=other.id)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active" and body["user_id"] == customer.id
    sub_id = body["id"]

    assert make_sub(client, c, catalog).status_code == 409  # duplicate number
    assert make_sub(client, c, catalog, msisdn="12345").status_code == 422  # bad number
    assert make_sub(client, c, catalog, msisdn="9000000001", plan="old").status_code == 422  # inactive plan
    r = client.post("/subscribers", json={"msisdn": "9000000002", "name": "X Y", "circle_id": 999}, headers=c)
    assert r.status_code == 404

    # Ownership: Amit cannot see Riya's number (not found, not forbidden).
    assert client.get(f"/subscribers/{sub_id}", headers=o).status_code == 404
    assert client.get("/subscribers", headers=o).json()["total"] == 0
    assert client.get("/subscribers", headers=c).json()["total"] == 1

    # Staff must say whose number it is.
    r = make_sub(client, s, catalog, msisdn="9123456780", name="Amit Shah", plan=None)
    assert r.status_code == 422
    r = make_sub(client, s, catalog, msisdn="9123456780", name="Amit Shah", plan=None, user_id=other.id)
    assert r.status_code == 201 and r.json()["user_id"] == other.id
    second_id = r.json()["id"]
    assert make_sub(client, s, catalog, msisdn="9000000003", user_id=9999).status_code == 404

    assert client.get("/subscribers", headers=s).json()["total"] == 2
    assert client.get("/subscribers?search=Riya", headers=s).json()["total"] == 1
    assert client.get("/subscribers?search=9123", headers=s).json()["total"] == 1
    assert client.get("/subscribers?status=active", headers=s).json()["total"] == 2
    assert client.get(f"/subscribers?circle_id={catalog['circle']}", headers=s).json()["total"] == 2
    assert client.get(f"/subscribers?plan_id={catalog['basic']}", headers=s).json()["total"] == 1

    # Plan change writes history.
    r = client.post(f"/subscribers/{sub_id}/change-plan", json={"new_plan_id": catalog["mega"]}, headers=c)
    assert r.status_code == 200 and r.json()["plan_id"] == catalog["mega"]
    assert client.post(f"/subscribers/{sub_id}/change-plan", json={"new_plan_id": catalog["mega"]}, headers=c).status_code == 422
    assert client.post(f"/subscribers/{sub_id}/change-plan", json={"new_plan_id": catalog["old"]}, headers=c).status_code == 422
    assert client.post(f"/subscribers/{sub_id}/change-plan", json={"new_plan_id": 9999}, headers=c).status_code == 404
    history = client.get(f"/subscribers/{sub_id}/plan-history", headers=c).json()
    assert [(h["old_plan_id"], h["new_plan_id"]) for h in history] == [
        (catalog["basic"], catalog["mega"]),
        (None, catalog["basic"]),
    ]

    # Editing is for staff only.
    assert client.patch(f"/subscribers/{sub_id}", json={"name": "Hacker"}, headers=c).status_code == 403
    r = client.patch(f"/subscribers/{sub_id}", json={"name": "Riya P", "plan_id": catalog["basic"]}, headers=s)
    assert r.status_code == 200 and r.json()["name"] == "Riya P" and r.json()["plan_id"] == catalog["basic"]
    assert client.patch(f"/subscribers/{sub_id}", json={"plan_id": None}, headers=s).status_code == 422
    assert client.patch(f"/subscribers/{sub_id}", json={"circle_id": 999}, headers=s).status_code == 404

    # A circle used by subscribers cannot be deleted.
    assert client.delete(f"/circles/{catalog['circle']}", headers=s).status_code == 409

    # Ported-out numbers cannot change plan or be reactivated.
    assert client.patch(f"/subscribers/{sub_id}", json={"status": "ported_out"}, headers=s).status_code == 200
    assert client.patch(f"/subscribers/{sub_id}", json={"status": "active"}, headers=s).status_code == 422
    assert client.post(f"/subscribers/{sub_id}/change-plan", json={"new_plan_id": catalog["mega"]}, headers=s).status_code == 422
    assert client.delete(f"/subscribers/{sub_id}", headers=s).json()["status"] == "ported_out"

    # Soft delete: staff only, the row stays and becomes inactive.
    assert client.delete(f"/subscribers/{second_id}", headers=c).status_code == 404
    assert client.delete(f"/subscribers/{second_id}", headers=o).status_code == 403
    assert client.delete(f"/subscribers/{second_id}", headers=s).json()["status"] == "inactive"
    assert client.get(f"/subscribers/{second_id}", headers=s).status_code == 200


def test_plan_in_use_is_deactivated_not_deleted(client, auth, admin, customer, catalog):
    make_sub(client, auth(customer), catalog)  # uses the "basic" plan
    r = client.delete(f"/plans/{catalog['basic']}", headers=auth(admin))
    assert r.json() == {"result": "deactivated"}
    assert client.get(f"/plans/{catalog['basic']}", headers=auth(admin)).json()["is_active"] is False


# ------------------------------------------------------------------- recharges


def test_recharge_flow(client, auth, customer, other, staff, catalog):
    c, o, s = auth(customer), auth(other), auth(staff)
    sub_id = make_sub(client, c, catalog).json()["id"]

    # The client tries to pay 1 rupee: the amount comes from the plan.
    r = client.post("/recharges", json={"subscriber_id": sub_id, "plan_id": catalog["mega"], "amount": 1}, headers=c)
    assert r.status_code == 201
    recharge = r.json()
    assert float(recharge["amount"]) == 599.0 and recharge["status"] == "pending"
    rid = recharge["id"]

    assert client.post("/recharges", json={"subscriber_id": sub_id, "plan_id": catalog["mega"]}, headers=o).status_code == 404
    assert client.post("/recharges", json={"subscriber_id": sub_id, "plan_id": catalog["old"]}, headers=c).status_code == 422
    assert client.post("/recharges", json={"subscriber_id": sub_id, "plan_id": 9999}, headers=c).status_code == 404
    assert client.post("/recharges", json={"subscriber_id": 9999, "plan_id": catalog["mega"]}, headers=c).status_code == 404

    # Only staff record the payment result.
    ok = {"status": "successful", "payment_reference": "PAY123"}
    assert client.patch(f"/recharges/{rid}/status", json=ok, headers=c).status_code == 403
    assert client.patch(f"/recharges/{rid}/status", json={"status": "pending"}, headers=s).status_code == 422
    r = client.patch(f"/recharges/{rid}/status", json=ok, headers=s)
    assert r.status_code == 200 and r.json()["status"] == "successful" and r.json()["payment_reference"] == "PAY123"
    assert client.get(f"/subscribers/{sub_id}", headers=c).json()["plan_id"] == catalog["mega"]  # plan activated
    assert len(client.get(f"/subscribers/{sub_id}/plan-history", headers=c).json()) == 2
    assert client.patch(f"/recharges/{rid}/status", json={"status": "failed"}, headers=s).status_code == 422  # locked

    # A second recharge that fails does not change the plan.
    r2 = client.post("/recharges", json={"subscriber_id": sub_id, "plan_id": catalog["basic"]}, headers=c).json()["id"]
    assert client.patch(f"/recharges/{r2}/status", json={"status": "failed"}, headers=s).status_code == 200
    assert client.get(f"/subscribers/{sub_id}", headers=c).json()["plan_id"] == catalog["mega"]

    # Lists, filters and ownership.
    assert client.get("/recharges", headers=c).json()["total"] == 2
    assert client.get("/recharges", headers=o).json()["total"] == 0
    assert client.get("/recharges?status=failed", headers=s).json()["total"] == 1
    assert client.get(f"/recharges?subscriber_id={sub_id}&plan_id={catalog['mega']}", headers=s).json()["total"] == 1
    assert client.get("/recharges?status=bogus", headers=s).status_code == 422
    assert client.get(f"/recharges/{rid}", headers=c).status_code == 200
    assert client.get(f"/recharges/{rid}", headers=o).status_code == 404
    assert client.get("/recharges/9999", headers=s).status_code == 404

    # A ported-out number cannot be recharged.
    client.patch(f"/subscribers/{sub_id}", json={"status": "ported_out"}, headers=s)
    r = client.post("/recharges", json={"subscriber_id": sub_id, "plan_id": catalog["basic"]}, headers=s)
    assert r.status_code == 422


# ----------------------------------------------------------------------- usage


def test_usage_mixed_units_summary_and_rules(client, auth, customer, other, staff, catalog):
    c, o, s = auth(customer), auth(other), auth(staff)
    sub_id = make_sub(client, c, catalog).json()["id"]

    r1 = client.post("/usage", json={"subscriber_id": sub_id, "usage_date": iso_ago(1), "raw_value": 500, "unit": "MB"}, headers=s)
    r2 = client.post("/usage", json={"subscriber_id": sub_id, "usage_date": iso_ago(1, aware=True), "raw_value": 1.5, "unit": "GB"}, headers=s)
    assert (r1.status_code, r2.status_code) == (201, 201)
    assert r1.json()["data_mb"] == 500.0 and r2.json()["data_mb"] == 1536.0
    assert r2.json()["raw_value"] == 1.5 and r2.json()["unit"] == "GB"  # original kept

    summary = client.get(f"/usage/summary/{sub_id}", headers=c).json()
    assert summary["total_mb"] == 2036.0 and summary["record_count"] == 2

    body = {"subscriber_id": sub_id, "usage_date": iso_ago(1), "raw_value": 1, "unit": "MB"}
    assert client.post("/usage", json=body, headers=c).status_code == 403
    assert client.post("/usage", json={**body, "usage_date": iso_ago(-5)}, headers=s).status_code == 422  # future
    assert client.post("/usage", json={**body, "unit": "KB"}, headers=s).status_code == 422
    assert client.post("/usage", json={**body, "raw_value": 0}, headers=s).status_code == 422
    assert client.post("/usage", json={**body, "subscriber_id": 9999}, headers=s).status_code == 404

    assert client.get("/usage", headers=c).json()["total"] == 2
    assert client.get("/usage", headers=o).json()["total"] == 0
    assert client.get(f"/usage/summary/{sub_id}", headers=o).status_code == 404
    assert client.get(f"/usage?subscriber_id={sub_id}&date_from={iso_ago(2)}", headers=s).json()["total"] == 2
    assert client.get(f"/usage?date_from={iso_ago(0)}", headers=s).json()["total"] == 0
    assert client.get(f"/usage?date_to={iso_ago(2)}", headers=s).json()["total"] == 0
    uid = r1.json()["id"]
    assert client.get(f"/usage/{uid}", headers=c).status_code == 200
    assert client.get(f"/usage/{uid}", headers=o).status_code == 404
    assert client.get("/usage/9999", headers=s).status_code == 404

    # Messy but allowed: a ported-out number still receives usage rows.
    client.patch(f"/subscribers/{sub_id}", json={"status": "ported_out"}, headers=s)
    assert client.post("/usage", json=body, headers=s).status_code == 201


# ------------------------------------------------------------------ complaints


def test_complaint_duplicates_filters_and_rules(client, auth, customer, other, staff, catalog):
    c, o, s = auth(customer), auth(other), auth(staff)
    sub_id = make_sub(client, c, catalog).json()["id"]

    # Same problem from the app and the call centre.
    first = client.post("/complaints", json={"subscriber_id": sub_id, "channel": "app", "category": "network", "description": "No signal since morning"}, headers=c).json()
    second = client.post("/complaints", json={"subscriber_id": sub_id, "channel": "call_centre", "category": "network", "description": "Customer reports no signal"}, headers=s).json()
    third = client.post("/complaints", json={"subscriber_id": sub_id, "channel": "app", "category": "billing", "description": "Charged twice for recharge"}, headers=c).json()
    assert first["status"] == "open" and first["linked_to_id"] is None
    assert second["linked_to_id"] == first["id"] and second["dedupe_key"] == first["dedupe_key"]
    assert third["linked_to_id"] is None

    assert client.get("/complaints?duplicates_only=true", headers=s).json()["total"] == 1
    assert client.get("/complaints?duplicates_only=false", headers=s).json()["total"] == 2
    assert client.get("/complaints?category=network", headers=s).json()["total"] == 2
    assert client.get("/complaints?channel=call_centre", headers=s).json()["total"] == 1
    assert client.get(f"/complaints?subscriber_id={sub_id}", headers=s).json()["total"] == 3
    assert client.get("/complaints", headers=c).json()["total"] == 3
    assert client.get("/complaints", headers=o).json()["total"] == 0

    bad = {"subscriber_id": sub_id, "channel": "app", "category": "sim", "description": "Trying to file for Riya"}
    assert client.post("/complaints", json=bad, headers=o).status_code == 404
    assert client.post("/complaints", json={**bad, "category": "weather"}, headers=c).status_code == 422
    assert client.post("/complaints", json={**bad, "description": "hi"}, headers=c).status_code == 422
    assert client.post("/complaints", json={**bad, "channel": "email"}, headers=c).status_code == 422

    fid = first["id"]
    assert client.patch(f"/complaints/{fid}/status", json={"status": "closed"}, headers=c).status_code == 403
    assert client.patch(f"/complaints/{fid}/status", json={"status": "done"}, headers=s).status_code == 422
    assert client.patch(f"/complaints/{fid}/status", json={"status": "in_progress"}, headers=s).json()["status"] == "in_progress"
    assert client.get("/complaints?status=in_progress", headers=s).json()["total"] == 1
    assert client.get(f"/complaints/{fid}", headers=c).status_code == 200
    assert client.get(f"/complaints/{fid}", headers=o).status_code == 404
    assert client.get("/complaints/9999", headers=s).status_code == 404