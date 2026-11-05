from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero

if TYPE_CHECKING:
    from app.modules.ventas.models import RenglonVenta


class Libro(SQLModel, table=True):
    __tablename__ = "libro"
    __table_args__ = (
        UniqueConstraint("isbn", name="uq_libro_isbn"),
        CheckConstraint("precio > 0", name="ck_libro_precio_positive"),
        CheckConstraint("stock >= 0", name="ck_libro_stock_non_negative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(max_length=20)
    titulo: str = Field(max_length=200)
    precio: Decimal = Field(max_digits=10, decimal_places=2)
    stock: int = Field(default=0)
    editorial_id: int = Field(foreign_key="editorial.id", index=True)
    genero_id: int | None = Field(default=None, foreign_key="genero.id", index=True)

    editorial: Editorial = Relationship(back_populates="libros")
    genero: Genero | None = Relationship(back_populates="libros")
    autorias: list["LibroAutor"] = Relationship(back_populates="libro")
    renglones: list["RenglonVenta"] = Relationship(back_populates="libro")


class LibroAutor(SQLModel, table=True):
    __tablename__ = "libro_autor"
    __table_args__ = (
        CheckConstraint("orden >= 1", name="ck_libro_autor_orden"),
        CheckConstraint(
            "rol IN ('autor', 'coautor', 'traductor', 'ilustrador')",
            name="ck_libro_autor_rol",
        ),
    )

    libro_id: int = Field(foreign_key="libro.id", primary_key=True, index=True)
    autor_id: int = Field(foreign_key="autor.id", primary_key=True, index=True)
    rol: str = Field(max_length=20)
    orden: int = Field()

    libro: Libro = Relationship(back_populates="autorias")
    autor: Autor = Relationship(back_populates="libro_autorias")
