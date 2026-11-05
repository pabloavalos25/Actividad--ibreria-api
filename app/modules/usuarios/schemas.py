from typing import Annotated, Literal
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, AfterValidator, field_validator


def limite_bytes(value: str) -> str:
    if len(value.encode('utf-8')) > 72:
        raise ValueError('La contraseña admite como máximo 72 bytes UTF-8')
    return value


Password = Annotated[str, Field(min_length=1), AfterValidator(limite_bytes)]
NuevaPassword = Annotated[str, Field(min_length=8), AfterValidator(limite_bytes)]


class Entrada(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Registro(Entrada):
    nombre: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=255)
    password: NuevaPassword


class Login(Entrada):
    email: EmailStr = Field(max_length=255)
    password: Password


class CambiarPassword(Entrada):
    password_actual: Password
    password_nueva: NuevaPassword


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    email: str
    activo: bool
    debe_cambiar_password: bool


class LoginRead(BaseModel):
    mensaje: str
    debe_cambiar_password: bool
    expira_en_segundos: int


class SesionRead(BaseModel):
    usuario: UsuarioRead
    roles_vigentes: list[str]
    roles_token: list[str]


Rol = Literal['ADMIN', 'VENDEDOR', 'CLIENTE']


class PersonalCreate(Entrada):
    nombre: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=255)
    password_provisoria: NuevaPassword
    rol: Literal['ADMIN', 'VENDEDOR']


class RolCreate(Entrada):
    rol: Rol
    vence_en: datetime | None = None

    @field_validator('vence_en')
    @classmethod
    def vencimiento_futuro(cls, value):
        if value is not None and (value.utcoffset() is None or value <= datetime.now(timezone.utc)):
            raise ValueError('El vencimiento debe tener zona horaria y ser futuro')
        return value


class RolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int
    rol: str
    desde: datetime
    vence_en: datetime | None
    revocada_en: datetime | None
    otorgada_por: int | None


class EventoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cuando: datetime
    actor: str
    accion: str
