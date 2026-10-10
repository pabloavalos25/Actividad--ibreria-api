from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.autores import service
from app.modules.autores.schemas import (
    AutorCreate,
    AutorRead,
    AutorUpdate,
    LibroConRol,
)

router = APIRouter(prefix="/autores", tags=["autores"])


@router.post("/", response_model=AutorRead, status_code=201)
async def crear_autor(
    datos: AutorCreate,
    session: AsyncSession = Depends(get_session),
) -> AutorRead:
    autor = await service.crear_autor(session, datos)
    return AutorRead.model_validate(autor, from_attributes=True)


@router.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(
    autor_id: int,
    session: AsyncSession = Depends(get_session),
) -> AutorRead:
    autor = await service.obtener_autor(session, autor_id)
    return AutorRead.model_validate(autor, from_attributes=True)


@router.patch("/{autor_id}", response_model=AutorRead)
async def actualizar_autor(
    autor_id: int,
    datos: AutorUpdate,
    session: AsyncSession = Depends(get_session),
) -> AutorRead:
    autor = await service.actualizar_autor(session, autor_id, datos)
    return AutorRead.model_validate(autor, from_attributes=True)


@router.get("/{autor_id}/libros", response_model=list[LibroConRol])
async def listar_libros_de_autor(
    autor_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[LibroConRol]:
    return await service.listar_libros_de_autor(session, autor_id)
