from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroRead

router = APIRouter(prefix="/generos", tags=["generos"])


@router.post("/", response_model=GeneroRead, status_code=201)
async def crear_genero(
    datos: GeneroCreate,
    session: AsyncSession = Depends(get_session),
) -> GeneroRead:
    genero = await service.crear_genero(session, datos)
    return GeneroRead.model_validate(genero, from_attributes=True)


@router.get("/", response_model=list[GeneroRead])
async def listar_generos(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[GeneroRead]:
    generos = await service.listar_generos(session, limit, offset)
    return [GeneroRead.model_validate(g, from_attributes=True) for g in generos]


@router.get("/{genero_id}/libros", response_model=list[LibroRead])
async def listar_libros_de_genero(
    genero_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[LibroRead]:
    libros = await libros_service.listar_libros_de_genero(session, genero_id)
    return [LibroRead.model_validate(libro, from_attributes=True) for libro in libros]
