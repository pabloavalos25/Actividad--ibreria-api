from pydantic import ConfigDict
from sqlmodel import SQLModel, Field


class GeneroCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=100)


class GeneroUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(default=None, min_length=1, max_length=100)


class GeneroRef(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class GeneroRead(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
