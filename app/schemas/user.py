# app/schemas/user.py
# Job of this file: define the shape of user and login data going IN and OUT.
# Security rule: the response (UserRead) NEVER contains the password hash.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Literal means: the value must be exactly one of these three words.
Role = Literal["admin", "staff", "user"]


class UserCreate(BaseModel):
    """Public sign-up. There is NO role field here on purpose:
    if there were, anyone could register themselves as admin (mass assignment attack).
    The service layer will always set role = "user" for this route."""

    email: EmailStr  # must look like a real email address
    # min 8 = no weak passwords. max 72 = bcrypt only uses the first 72 bytes.
    password: str = Field(min_length=8, max_length=72)


class UserCreateByAdmin(UserCreate):
    """Used ONLY by admins, to create staff or admin accounts.
    It copies email + password from UserCreate and adds a role."""

    role: Role = "user"


class UserUpdate(BaseModel):
    """Admin changes a user. Every field is optional (send only what changes)."""

    role: Role | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    """What we send back. Notice: NO hashed_password field here."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    """What the client sends to log in."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class Token(BaseModel):
    """What we send back after a successful login."""

    access_token: str  # the JWT itself
    token_type: str = "bearer"  # tells the client how to send it back