# app/services/auth_service.py
# Job of this file: business rules for users: sign-up, admin-created users,
# login, and admin user management. It never touches the database directly;
# it asks UserRepository. Broken rules are raised as exceptions.

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import (
    LoginRequest,
    Token,
    UserCreate,
    UserCreateByAdmin,
    UserUpdate,
)

# A fake hash used when the email does not exist, so login takes about the
# same time whether the email exists or not (stops "email guessing" by timing).
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthService:
    def __init__(self, db: Session):
        self.users = UserRepository(db)

    def _create(self, email: str, password: str, role: str) -> User:
        """Shared by register and create_by_admin."""
        email = email.lower()  # save lowercase, because get_by_email searches lowercase
        if self.users.get_by_email(email):
            raise ConflictError("Email is already registered")
        user = User(email=email, hashed_password=hash_password(password), role=role)
        return self.users.add(user)

    def register(self, data: UserCreate) -> User:
        """Public sign-up. The role is ALWAYS 'user' (UserCreate has no role field)."""
        return self._create(data.email, data.password, role="user")

    def create_by_admin(self, data: UserCreateByAdmin) -> User:
        """Admin creates a user with any role. The router allows admins only."""
        return self._create(data.email, data.password, role=data.role)

    def login(self, data: LoginRequest) -> Token:
        """Check email + password and return a JWT."""
        user = self.users.get_by_email(data.email)

        # If the user doesn't exist we still do one password check (against the
        # dummy hash), then fail with the SAME message as a wrong password.
        stored_hash = user.hashed_password if user else _DUMMY_HASH
        password_ok = verify_password(data.password, stored_hash)
        if user is None or not password_ok:
            raise UnauthorizedError("Incorrect email or password")

        # Only after a correct password do we say the account is disabled.
        if not user.is_active:
            raise UnauthorizedError("This account is disabled")

        return Token(access_token=create_access_token(user.id))

    def get_user(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    def list_users(self, offset: int, limit: int) -> tuple[list[User], int]:
        return self.users.get_many(offset=offset, limit=limit)

    def update_user(self, user_id: int, data: UserUpdate, acting_user_id: int) -> User:
        """Admin changes a user's role or active flag."""
        user = self.get_user(user_id)
        changes = data.model_dump(exclude_unset=True)  # only what the client sent

        # Safety rule: an admin must not lock themselves out.
        if user_id == acting_user_id:
            if changes.get("is_active") is False or (
                "role" in changes and changes["role"] != "admin"
            ):
                raise BusinessRuleError("You cannot disable or demote your own account")

        return self.users.update(user, changes)