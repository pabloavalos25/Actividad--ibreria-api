from decimal import Decimal

from pydantic import ConfigDict
from sqlmodel import SQLModel, Field


class AutorCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=100)
    nacionalidad: str = Field(min_length=1, max_length=100)


class AutorUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(default=None, min_length=1, max_length=100)
    nacionalidad: str = Field(default=None, min_length=1, max_length=100)


class AutorRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nacionalidad: str


class LibroConRol(SQLModel):
    libro_id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    rol: str
    orden: int
