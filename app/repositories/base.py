# app/repositories/base.py
# Job of this file: the 5 database jobs every table needs (get, get many, add,
# update, delete), written ONCE. Every other repository reuses this class.

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base

# ModelType is a placeholder for "any model" (Plan, Subscriber, ...).
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: Session, model: type[ModelType]):
        self.db = db        # the session (one conversation with the database)
        self.model = model  # which table this repository works on

    def get(self, item_id: int) -> ModelType | None:
        """Find one row by its id. Returns None if it does not exist."""
        return self.db.get(self.model, item_id)

    def get_many(
        self,
        offset: int = 0,
        limit: int = 10,
        filters: list[Any] | None = None,
    ) -> tuple[list[ModelType], int]:
        """Return (rows of ONE page, total rows that match).
        'filters' are conditions like Plan.price <= 300, built by subclasses."""
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        # Apply every filter to both the data query and the count query,
        # so the total matches what the client is searching for.
        for condition in filters or []:
            query = query.where(condition)
            count_query = count_query.where(condition)

        total = self.db.scalar(count_query) or 0
        # order_by id = stable order, so pages don't shuffle between requests.
        rows = self.db.scalars(
            query.order_by(self.model.id).offset(offset).limit(limit)
        ).all()
        return list(rows), total

    def add(self, obj: ModelType) -> ModelType:
        """Save a new row. refresh() reloads it so id and created_at are filled in."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType, data: dict) -> ModelType:
        """Change only the fields given in 'data', then save."""
        for field, value in data.items():
            setattr(obj, field, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        """Remove a row for good."""
        self.db.delete(obj)
        self.db.commit()