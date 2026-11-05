from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.modules.clientes.models import Cliente
from app.modules.libros.models import Libro


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Venta(SQLModel, table=True):
    __tablename__ = "venta"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_venta_total_non_negative"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    fecha: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    total: Decimal = Field(max_digits=12, decimal_places=2)

    cliente: Cliente = Relationship(back_populates="ventas")
    renglones: list["RenglonVenta"] = Relationship(
        back_populates="venta",
        cascade_delete=True,
    )


class RenglonVenta(SQLModel, table=True):
    __tablename__ = "renglon_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_renglon_venta_cantidad_positive"),
        CheckConstraint(
            "precio_unitario > 0",
            name="ck_renglon_venta_precio_unitario_positive",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="venta.id", index=True)
    libro_id: int = Field(foreign_key="libro.id", index=True)
    cantidad: int = Field()
    precio_unitario: Decimal = Field(max_digits=10, decimal_places=2)

    venta: Venta = Relationship(back_populates="renglones")
    libro: Libro = Relationship(back_populates="renglones")
