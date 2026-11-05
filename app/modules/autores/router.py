from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.autores import service
from app.modules.autores.schemas import (
    AutorCreate,
    AutorRead,
    AutorUpdate,
    LibroConRol,
)

public_router = APIRouter(prefix="/autores", tags=["autores"])
protected_router = APIRouter(prefix="/autores", tags=["autores"])



@protected_router.post("/", response_model=AutorRead, status_code=201, dependencies=[Depends(requiere_admin)])
async def crear_autor(
    datos: AutorCreate,
    session: AsyncSession = Depends(get_session),
) -> AutorRead:
    autor = await service.crear_autor(session, datos)
    return AutorRead.model_validate(autor, from_attributes=True)


@public_router.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(
    autor_id: Annotated[int, Path(gt=0, le=2147483647)],
    session: AsyncSession = Depends(get_session),
) -> AutorRead:
    autor = await service.obtener_autor(session, autor_id)
    return AutorRead.model_validate(autor, from_attributes=True)


@protected_router.patch("/{autor_id}", response_model=AutorRead, dependencies=[Depends(requiere_admin)])
async def actualizar_autor(
    autor_id: Annotated[int, Path(gt=0, le=2147483647)],
    datos: AutorUpdate,
    session: AsyncSession = Depends(get_session),
) -> AutorRead:
    autor = await service.actualizar_autor(session, autor_id, datos)
    return AutorRead.model_validate(autor, from_attributes=True)


@public_router.get("/{autor_id}/libros", response_model=Pagina[LibroConRol])
async def listar_libros_de_autor(
    autor_id: Annotated[int, Path(gt=0, le=2147483647)],
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.listar_libros_de_autor(session, autor_id, page, size)


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
