# app/models/circle.py
# Job of this file: describe the "circles" table (telecom regions like Gujarat).

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Circle(Base):
    # The real table name in the database.
    __tablename__ = "circles"

    # Automatic unique number for each circle (1, 2, 3...).
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # unique=True    -> no two circles can have the same name.
    # nullable=False -> a circle must always have a name.
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)