# app/core/deps.py
# Job of this file: "dependencies" every router can plug in.
#   - get_current_user : who is calling? (reads the JWT, loads the user from the DB)
#   - require_roles    : is this role allowed in? (admin / staff / user)

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user import UserRepository

# Reads "Authorization: Bearer <token>". It also adds the Authorize button to /docs.
# auto_error=False -> if the header is missing we raise OUR error (same JSON shape).
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Turn the token into the real, current User from the database."""
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    # None = fake, tampered with, or expired token.
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")

    try:
        user_id = int(payload.get("sub", ""))  # "sub" holds the user id as text
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid or expired token")

    # The role is read FRESH from the database each time, never from the token,
    # so demoting or disabling someone works immediately.
    user = UserRepository(db).get(user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired token")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled")
    return user


def require_roles(*allowed_roles: str):
    """Build a gatekeeper that lets in only the given roles."""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError("You do not have permission for this action")
        return current_user

    return checker


# Ready-made gatekeepers for routers.
require_staff = require_roles("admin", "staff")  # employees: staff or admin
require_admin = require_roles("admin")  # admin only

# Shortcuts so router functions stay short:
#   def my_route(db: DbSession, user: CurrentUser): ...
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]