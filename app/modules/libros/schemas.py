from decimal import Decimal
from typing import Literal

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

from app.modules.editoriales.schemas import EditorialRef
from app.modules.generos.schemas import GeneroRef

RolAutor = Literal["autor", "coautor", "traductor", "ilustrador"]


class AutoriaCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    autor_id: int = Field(gt=0, le=2147483647)
    rol: RolAutor
    orden: int = Field(ge=1, le=2147483647)


class LibroCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    isbn: str = Field(min_length=1, max_length=20)
    titulo: str = Field(min_length=1, max_length=200)
    precio: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock_inicial: int = Field(ge=0, le=2147483647)
    editorial_id: int = Field(gt=0, le=2147483647)
    genero_id: int | None = None
    autores: list[AutoriaCreate] = []


class LibroUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(default=None, min_length=1, max_length=200)
    precio: Decimal = Field(default=None, gt=0, max_digits=10, decimal_places=2)


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
