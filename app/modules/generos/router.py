from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroRead

public_router = APIRouter(prefix="/generos", tags=["generos"])
protected_router = APIRouter(prefix="/generos", tags=["generos"])



@protected_router.post("/", response_model=GeneroRead, status_code=201, dependencies=[Depends(requiere_admin)])
async def crear_genero(
    datos: GeneroCreate,
    session: AsyncSession = Depends(get_session),
) -> GeneroRead:
    genero = await service.crear_genero(session, datos)
    return GeneroRead.model_validate(genero, from_attributes=True)


@public_router.get("/", response_model=Pagina[GeneroRead])
async def listar_generos(
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session),
) -> dict:
    generos = await service.listar_generos(session, page, size)
    generos["items"] = [GeneroRead.model_validate(g, from_attributes=True) for g in generos["items"]]
    return generos


@public_router.get("/{genero_id}/libros", response_model=Pagina[LibroRead])
async def listar_libros_de_genero(
    genero_id: Annotated[int, Path(gt=0, le=2147483647)],
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session),
) -> dict:
    libros = await libros_service.listar_libros_de_genero(
        session, genero_id, page, size
    )
    libros["items"] = [LibroRead.model_validate(libro, from_attributes=True) for libro in libros["items"]]
    return libros


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
