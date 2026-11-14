# app/repositories/circle.py
# Job of this file: database access for circles.
# It reuses BaseRepository and adds one special search: find a circle by name.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.circle import Circle
from app.repositories.base import BaseRepository


class CircleRepository(BaseRepository[Circle]):
    def __init__(self, db: Session):
        # Tell the parent class: "this repository works on the Circle table".
        super().__init__(db, Circle)

    def get_by_name(self, name: str) -> Circle | None:
        """Find a circle by its exact name (used to stop duplicate names)."""
        return self.db.scalar(select(Circle).where(Circle.name == name))