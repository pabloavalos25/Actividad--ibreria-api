from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.libros import service
from app.modules.libros.schemas import LibroDetalleRead, LibroRead, LibroUpdate

router = APIRouter(prefix="/libros", tags=["libros"])


@router.get("/", response_model=list[LibroRead])
async def listar_libros(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    titulo: str | None = Query(None),
    genero_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[LibroRead]:
    libros = await service.listar_libros(
        session, limit, offset, titulo, genero_id
    )
    return [LibroRead.model_validate(libro, from_attributes=True) for libro in libros]


@router.get("/{libro_id}", response_model=LibroDetalleRead)
async def obtener_libro(
    libro_id: int,
    session: AsyncSession = Depends(get_session),
) -> LibroDetalleRead:
    libro = await service.obtener_libro(session, libro_id)
    return service.detalle(libro)


@router.patch("/{libro_id}", response_model=LibroDetalleRead)
async def actualizar_libro(
    libro_id: int,
    datos: LibroUpdate,
    session: AsyncSession = Depends(get_session),
) -> LibroDetalleRead:
    libro = await service.actualizar_libro(session, libro_id, datos)
    return service.detalle(libro)
