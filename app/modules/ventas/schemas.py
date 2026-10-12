from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ConfigDict, computed_field, field_serializer, model_validator
from sqlmodel import SQLModel, Field

from app.modules.clientes.schemas import ClienteRef


class RenglonCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    libro_id: int
    cantidad: int = Field(gt=0)


class VentaCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    cliente_id: int
    renglones: list[RenglonCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def sin_libros_repetidos(self):
        ids = [r.libro_id for r in self.renglones]
        if len(ids) != len(set(ids)):
            raise ValueError("Un mismo libro no puede repetirse en dos renglones")
        return self


class RenglonRead(SQLModel):
    libro_id: int
    titulo: str
    cantidad: int
    precio_unitario: Decimal

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return self.precio_unitario * self.cantidad


class VentaRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteRef
    renglones: list[RenglonRead]

    @field_serializer("fecha")
    def serializar_fecha(self, fecha: datetime) -> str:
        return (
            fecha.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        )
