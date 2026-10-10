from pydantic import ConfigDict
from sqlmodel import SQLModel


class EditorialCreate(SQLModel):
    nombre: str
    pais: str


class EditorialUpdate(SQLModel):
    nombre: str | None = None
    pais: str | None = None


class EditorialRef(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class EditorialRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    pais: str
