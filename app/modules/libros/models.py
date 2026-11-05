from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import Field, Relationship, SQLModel

from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero

if TYPE_CHECKING:
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import RenglonVenta, Venta


class Libro(SQLModel, table=True):
    __tablename__ = "libro"
    __table_args__ = (
        Index('uq_libro_isbn_vigente', 'isbn', unique=True,
              postgresql_where=text('borrado_en IS NULL')),
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
    borrado_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    editorial: Editorial = Relationship(back_populates="libros")
    genero: Genero | None = Relationship(back_populates="libros")
    autorias: list["LibroAutor"] = Relationship(back_populates="libro")
    renglones: list["RenglonVenta"] = Relationship(back_populates="libro")
    movimientos: list['MovimientoStock'] = Relationship(
        back_populates='libro', sa_relationship_kwargs={'passive_deletes': 'all'},
    )


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


class MovimientoStock(SQLModel, table=True):
    __tablename__ = 'movimiento_stock'
    __table_args__ = (CheckConstraint('cantidad <> 0', name='ck_movimiento_stock_cantidad_no_cero'),)

    id: int | None = Field(default=None, primary_key=True)
    libro_id: int = Field(foreign_key='libro.id', index=True)
    venta_id: int | None = Field(default=None, foreign_key='venta.id', index=True)
    usuario_id: int = Field(foreign_key='usuario.id', index=True)
    cantidad: int = Field()
    motivo: str = Field()
    cuando: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), sa_type=DateTime(timezone=True),
    )

    libro: Libro = Relationship(back_populates='movimientos')
    venta: Optional['Venta'] = Relationship(back_populates='movimientos_stock')
    usuario: 'Usuario' = Relationship(back_populates='movimientos_stock')
