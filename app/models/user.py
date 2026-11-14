# app/models/user.py
# Job of this file: describe the "users" table (people who can log in).

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    # The real table name in the database.
    __tablename__ = "users"

    # primary_key=True -> every user gets a unique number (1, 2, 3...) automatically.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # unique=True  -> two users cannot have the same email.
    # nullable=False -> email can never be empty.
    # index=True   -> makes searching by email fast (we do this at every login).
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    # We NEVER store the real password. We store a scrambled version (a "hash")
    # made with bcrypt, so even we cannot read the original password.
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    # One of: "admin", "staff", "user". The services layer will check this value.
    role: Mapped[str] = mapped_column(String, nullable=False)

    # default=True -> a new user is active unless we say otherwise.
    # Setting this to False lets us block a user without deleting them.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # server_default=func.now() -> the database fills in the current time by itself.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())