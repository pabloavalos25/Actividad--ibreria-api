from decimal import Decimal

from pydantic import ConfigDict
from sqlmodel import SQLModel


class AutorCreate(SQLModel):
    nombre: str
    nacionalidad: str


class AutorUpdate(SQLModel):
    nombre: str | None = None
    nacionalidad: str | None = None


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
