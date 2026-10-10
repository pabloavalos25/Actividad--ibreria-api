from pydantic import ConfigDict
from sqlmodel import SQLModel


class ClienteCreate(SQLModel):
    nombre: str
    email: str


class ClienteUpdate(SQLModel):
    nombre: str | None = None
    email: str | None = None


class PerfilCreate(SQLModel):
    telefono: str | None = None
    direccion: str | None = None


class PerfilRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    telefono: str | None = None
    direccion: str | None = None


class ClienteRef(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str


class ClienteRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    perfil: PerfilRead | None = None
