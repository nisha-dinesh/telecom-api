# tests/conftest.py
# Job of this file: shared "fixtures" (ready-made helpers) for all tests.
# Every test gets a FRESH in-memory database, so tests never affect each other.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers all tables)
from app.core.database import Base, get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.circle import Circle
from app.models.plan import Plan
from app.models.user import User

limiter.enabled = False  # switch rate limiting off (one test switches it on again)

PASSWORD = "Password@123"
HASHED = hash_password(PASSWORD)  # hash ONCE: bcrypt is slow on purpose


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine):
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture()
def client(engine):
    """A fake browser talking to our app, wired to the temporary database."""

    def override_get_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db):
    """Returns a function that creates a user straight in the database."""

    def _make(email, role="user", is_active=True):
        user = User(email=email, hashed_password=HASHED, role=role, is_active=is_active)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture()
def admin(make_user):
    return make_user("admin@example.com", "admin")


@pytest.fixture()
def staff(make_user):
    return make_user("staff@example.com", "staff")


@pytest.fixture()
def customer(make_user):
    return make_user("riya@example.com", "user")


@pytest.fixture()
def other(make_user):
    return make_user("amit@example.com", "user")


@pytest.fixture()
def auth():
    """Returns a function: user -> {'Authorization': 'Bearer <token>'}."""

    def _headers(user):
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return _headers


@pytest.fixture()
def catalog(db):
    """One circle and three plans (one inactive). Returns their ids."""
    circle = Circle(name="Gujarat")
    basic = Plan(name="Basic 199", price=199, validity_days=28, data_mb_per_day=1024)
    mega = Plan(name="Mega 599", price=599, validity_days=84, data_mb_per_day=2048)
    old = Plan(name="Old 99", price=99, validity_days=14, data_mb_per_day=512, is_active=False)
    db.add_all([circle, basic, mega, old])
    db.commit()
    return {"circle": circle.id, "basic": basic.id, "mega": mega.id, "old": old.id}