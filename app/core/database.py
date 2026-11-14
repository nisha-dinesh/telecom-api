# app/core/database.py
# Job of this file: connect to the database and give out sessions.

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# SQLite only: by default it refuses to be used from more than one thread.
# FastAPI uses several threads, so for SQLite we switch that check off.
# PostgreSQL does not need this, so for it we pass nothing.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# The ENGINE = the connection to the database (made once, from the URL in .env).
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# SessionLocal is a "factory": every time we call SessionLocal() we get a new session.
# autocommit=False -> nothing is saved until we call session.commit()
# autoflush=False  -> we decide when changes are sent to the database
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Parent class of all models. Every table class will inherit from this."""
    pass


def get_db():
    """Gives ONE session to each request, and always closes it at the end.

    'yield' means: hand the session to the request, wait until the request
    is finished, then run the 'finally' part to close the session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()