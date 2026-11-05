from pydantic import ConfigDict
from sqlmodel import SQLModel, Field


class EditorialCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=100)
    pais: str = Field(min_length=1, max_length=100)


class EditorialUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(default=None, min_length=1, max_length=100)
    pais: str = Field(default=None, min_length=1, max_length=100)


class EditorialRef(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class EditorialRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    pais: str
