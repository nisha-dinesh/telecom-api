# app/schemas/circle.py
# Job of this file: define the shape of circle data going IN and OUT of the API.

from pydantic import BaseModel, ConfigDict, Field


class CircleCreate(BaseModel):
    """What the client sends to create a circle."""

    # min_length=2 -> at least 2 letters. max_length=50 -> stops huge junk input.
    name: str = Field(min_length=2, max_length=50, examples=["Gujarat"])


class CircleUpdate(BaseModel):
    """What the client sends to rename a circle."""

    name: str = Field(min_length=2, max_length=50)


class CircleRead(BaseModel):
    """What we send back to the client."""

    # from_attributes=True lets Pydantic read data straight from a database
    # model object (circle.id, circle.name) instead of only from a dictionary.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str