from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ConfigDict, computed_field, field_serializer
from sqlmodel import SQLModel

from app.modules.clientes.schemas import ClienteRef


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
