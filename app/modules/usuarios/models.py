from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Index, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import MovimientoStock


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(SQLModel, table=True):
    __tablename__ = 'usuario'
    __table_args__ = (UniqueConstraint('email', name='uq_usuario_email'),)

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255)
    nombre: str = Field(max_length=100)
    password_hash: str = Field(max_length=255)
    activo: bool = Field(default=True)
    debe_cambiar_password: bool = Field(default=False)

    cliente: Optional['Cliente'] = Relationship(
        back_populates='usuario', sa_relationship_kwargs={'uselist': False},
    )
    asignaciones: list['AsignacionRol'] = Relationship(
        back_populates='usuario',
        sa_relationship_kwargs={'foreign_keys': 'AsignacionRol.usuario_id', 'passive_deletes': 'all'},
    )
    asignaciones_otorgadas: list['AsignacionRol'] = Relationship(
        back_populates='otorgante',
        sa_relationship_kwargs={'foreign_keys': 'AsignacionRol.otorgada_por', 'passive_deletes': 'all'},
    )
    movimientos_stock: list['MovimientoStock'] = Relationship(
        back_populates='usuario', sa_relationship_kwargs={'passive_deletes': 'all'},
    )


class AsignacionRol(SQLModel, table=True):
    __tablename__ = 'asignacion_rol'
    __table_args__ = (
        CheckConstraint("rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')", name='ck_asignacion_rol_rol'),
        Index('uq_asignacion_rol_abierta', 'usuario_id', 'rol', unique=True,
              postgresql_where=text('revocada_en IS NULL')),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key='usuario.id', index=True)
    rol: str = Field(max_length=20)
    desde: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    vence_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    revocada_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    otorgada_por: int | None = Field(default=None, foreign_key='usuario.id', index=True)

    usuario: Usuario = Relationship(
        back_populates='asignaciones', sa_relationship_kwargs={'foreign_keys': 'AsignacionRol.usuario_id'},
    )
    otorgante: Usuario | None = Relationship(
        back_populates='asignaciones_otorgadas',
        sa_relationship_kwargs={'foreign_keys': 'AsignacionRol.otorgada_por'},
    )


class IntentoAcceso(SQLModel, table=True):
    __tablename__ = 'intento_acceso'
    __table_args__ = (Index('ix_intento_acceso_email_ip_cuando', 'email', 'ip', 'cuando'),)

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    email: str = Field(max_length=255)
    ip: str = Field(max_length=45)
    exito: bool = Field()


class EventoSeguridad(SQLModel, table=True):
    __tablename__ = 'evento_seguridad'

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(default_factory=_utcnow, sa_type=DateTime(timezone=True))
    actor: str = Field(max_length=255)
    accion: str = Field()
