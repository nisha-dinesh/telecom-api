# app/repositories/user.py
# Job of this file: database access for users.
# It reuses BaseRepository and adds one search: find a user by email (for login).

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        """Find a user by email. Emails are compared in lowercase so
        'A@b.com' and 'a@b.com' are treated as the same person."""
        return self.db.scalar(select(User).where(User.email == email.lower()))
    