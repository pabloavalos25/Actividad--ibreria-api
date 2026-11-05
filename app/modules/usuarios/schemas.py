from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, AfterValidator


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
