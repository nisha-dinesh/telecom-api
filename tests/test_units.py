# tests/test_units.py
# Job of this file: small "unit" tests for single functions (no web requests).

from datetime import date

import jwt
import pytest

from app.core.exceptions import (
    AppError,
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.pagination import PaginationParams
from app.schemas.user import LoginRequest
from app.services.auth_service import AuthService
from app.services.complaint_service import make_dedupe_key
from app.services.usage_service import to_mb


def test_to_mb_converts_gb_and_keeps_mb():
    assert to_mb(1.5, "GB") == 1536.0
    assert to_mb(500, "MB") == 500.0
    assert to_mb(0.001, "GB") == 1.024  # rounded, no float noise


def test_dedupe_key_has_subscriber_category_and_todays_date():
    subscriber_id, category, day = make_dedupe_key(5, "network").split("|")
    assert (subscriber_id, category) == ("5", "network")
    date.fromisoformat(day)  # raises an error if it is not a real date


def test_password_hashing():
    hashed = hash_password("secret123")
    assert hashed != "secret123" and hashed.startswith("$2b$")
    assert hash_password("secret123") != hashed  # random salt
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("secret123", "not-a-real-hash")  # broken hash = False


def test_long_passwords_hash_and_verify_the_same_way():
    long_password = "a" * 100
    assert verify_password(long_password, hash_password(long_password))


def test_jwt_roundtrip_and_tampering():
    token = create_access_token(7)
    assert decode_access_token(token)["sub"] == "7"
    assert "role" not in decode_access_token(token)
    assert decode_access_token(token + "x") is None
    assert decode_access_token("garbage") is None
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


@pytest.mark.parametrize(
    "error_class, code",
    [
        (NotFoundError, 404),
        (ConflictError, 409),
        (ForbiddenError, 403),
        (UnauthorizedError, 401),
        (BusinessRuleError, 422),
    ],
)
def test_exceptions_carry_status_and_message(error_class, code):
    error = error_class("custom text")
    assert error.status_code == code
    assert error.message == "custom text"
    assert isinstance(error, AppError)
    assert error_class().message  # default message exists


def test_pagination_offset():
    assert PaginationParams(page=1, page_size=10).offset == 0
    assert PaginationParams(page=3, page_size=10).offset == 20


def test_login_with_unknown_email_gives_the_generic_error(db):
    with pytest.raises(UnauthorizedError, match="Incorrect email or password"):
        AuthService(db).login(LoginRequest(email="nobody@example.com", password="whatever1"))