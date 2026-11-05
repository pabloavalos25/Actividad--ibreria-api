from pydantic import ConfigDict
from sqlmodel import SQLModel, Field


class ClienteCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=255)


class ClienteUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(default=None, min_length=1, max_length=100)
    email: str = Field(default=None, min_length=1, max_length=255)


class PerfilCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    telefono: str | None = Field(default=None, max_length=30)
    direccion: str | None = Field(default=None, max_length=255)


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
