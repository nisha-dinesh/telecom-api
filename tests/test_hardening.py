# tests/test_hardening.py
# Job of this file: tests for the safety layer (headers, size limit, errors, rate limit).

from app.core.limiter import limiter
from app.main import app


@app.get("/boom")  # a deliberately broken route, only used by these tests
def boom():
    raise RuntimeError("secret internal detail")


def test_security_headers_and_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-request-id"]


def test_huge_body_is_refused(client):
    r = client.post("/auth/login", content="x" * 1_100_000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_unexpected_error_never_leaks_details(client):
    r = client.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"error": {"code": 500, "message": "Internal server error"}}
    assert "secret" not in r.text and "Traceback" not in r.text


def test_login_is_rate_limited(client):
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.post("/auth/login", json={"email": "a@example.com", "password": "wrongpass1"}).status_code
            for _ in range(6)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert codes == [401, 401, 401, 401, 401, 429]