from pydantic import ConfigDict
from sqlmodel import SQLModel


class GeneroCreate(SQLModel):
    nombre: str


class GeneroUpdate(SQLModel):
    nombre: str | None = None


class GeneroRef(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class GeneroRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
