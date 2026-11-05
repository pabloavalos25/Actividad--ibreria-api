from typing import TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.modules.usuarios.models import Usuario

if TYPE_CHECKING:
    from app.modules.ventas.models import Venta


class PerfilCliente(SQLModel, table=True):
    __tablename__ = "perfil_cliente"
    __table_args__ = (
        UniqueConstraint("cliente_id", name="uq_perfil_cliente_cliente_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    telefono: str | None = Field(default=None, max_length=30)
    direccion: str | None = Field(default=None, max_length=255)

    cliente: "Cliente" = Relationship(back_populates="perfil")


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"
    __table_args__ = (
        UniqueConstraint("email", name="uq_cliente_email"),
        UniqueConstraint("usuario_id", name="uq_cliente_usuario_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100)
    email: str = Field(max_length=255)
    usuario_id: int | None = Field(default=None, foreign_key='usuario.id', index=True)

    usuario: Usuario | None = Relationship(
        back_populates='cliente', sa_relationship_kwargs={'uselist': False},
    )

    perfil: PerfilCliente | None = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False},
    )
    ventas: list["Venta"] = Relationship(back_populates="cliente")
