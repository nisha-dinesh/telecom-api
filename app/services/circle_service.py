# app/services/circle_service.py
# Job of this file: business rules for circles (regions like Gujarat).

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.circle import Circle
from app.repositories.circle import CircleRepository
from app.repositories.subscriber import SubscriberRepository
from app.schemas.circle import CircleCreate, CircleUpdate


class CircleService:
    def __init__(self, db: Session):
        self.circles = CircleRepository(db)
        self.subscribers = SubscriberRepository(db)

    def create(self, data: CircleCreate) -> Circle:
        name = data.name.strip()
        if self.circles.get_by_name(name):  # Rule 1: no duplicate names
            raise ConflictError(f"Circle '{name}' already exists")
        return self.circles.add(Circle(name=name))

    def get(self, circle_id: int) -> Circle:
        circle = self.circles.get(circle_id)
        if circle is None:
            raise NotFoundError(f"Circle {circle_id} not found")
        return circle

    def list(self, offset: int, limit: int) -> tuple[list[Circle], int]:
        return self.circles.get_many(offset=offset, limit=limit)

    def update(self, circle_id: int, data: CircleUpdate) -> Circle:
        circle = self.get(circle_id)
        name = data.name.strip()
        other = self.circles.get_by_name(name)
        if other and other.id != circle_id:  # the name may be this circle's own
            raise ConflictError(f"Circle '{name}' already exists")
        return self.circles.update(circle, {"name": name})

    def delete(self, circle_id: int) -> None:
        circle = self.get(circle_id)
        filters = SubscriberRepository.build_filters(circle_id=circle_id)
        _, in_use = self.subscribers.get_many(offset=0, limit=1, filters=filters)
        if in_use:  # Rule 2: cannot delete a circle that subscribers use
            raise ConflictError("Circle is used by subscribers and cannot be deleted")
        self.circles.delete(circle)