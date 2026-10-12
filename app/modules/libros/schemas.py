from decimal import Decimal
from typing import Literal

from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.modules.editoriales.schemas import EditorialRef
from app.modules.generos.schemas import GeneroRef

RolAutor = Literal["autor", "coautor", "traductor", "ilustrador"]


class AutoriaCreate(SQLModel):
    autor_id: int
    rol: RolAutor
    orden: int


class LibroCreate(SQLModel):
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None = None
    autores: list[AutoriaCreate] = []


class LibroUpdate(SQLModel):
    isbn: str | None = None
    titulo: str | None = None
    precio: Decimal | None = None
    stock: int | None = None
    editorial_id: int | None = None
    genero_id: int | None = None


class AutorConRol(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    autor_id: int
    nombre: str
    rol: str
    orden: int


class LibroRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: EditorialRef
    genero: GeneroRef | None = None


class LibroDetalleRead(LibroRead):
    autores: list[AutorConRol] = []
