from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import requerir_usuario_id
from app.modules.libros import service
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetalleRead,
    LibroRead,
    LibroUpdate,
)

public_router = APIRouter(prefix="/libros", tags=["libros"])
protected_router = APIRouter(prefix="/libros", tags=["libros"])



@protected_router.post("/", response_model=LibroDetalleRead, status_code=201, dependencies=[Depends(requiere_admin)])
async def crear_libro(
    datos: LibroCreate,
    usuario_id: int = Depends(requerir_usuario_id),
    session: AsyncSession = Depends(get_session),
) -> LibroDetalleRead:
    libro = await service.crear_libro(session, datos, usuario_id=usuario_id)
    return service.detalle(libro)


@protected_router.delete('/{libro_id}', status_code=204, dependencies=[Depends(requiere_admin)])
async def eliminar_libro(libro_id: Annotated[int, Path(gt=0, le=2147483647)], session: AsyncSession = Depends(get_session)) -> Response:
    await service.eliminar_libro(session, libro_id)
    return Response(status_code=204)


@public_router.get("/", response_model=Pagina[LibroRead])
async def listar_libros(
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    titulo: str | None = Query(None),
    genero_id: int | None = Query(None, gt=0, le=2147483647),
    session: AsyncSession = Depends(get_session),
) -> dict:
    libros = await service.listar_libros(
        session, page, size, titulo, genero_id
    )
    libros["items"] = [LibroRead.model_validate(libro, from_attributes=True) for libro in libros["items"]]
    return libros


@public_router.get("/{libro_id}", response_model=LibroDetalleRead)
async def obtener_libro(
    libro_id: Annotated[int, Path(gt=0, le=2147483647)],
    session: AsyncSession = Depends(get_session),
) -> LibroDetalleRead:
    libro = await service.obtener_libro(session, libro_id)
    return service.detalle(libro)


@protected_router.patch("/{libro_id}", response_model=LibroDetalleRead, dependencies=[Depends(requiere_admin)])
async def actualizar_libro(
    libro_id: Annotated[int, Path(gt=0, le=2147483647)],
    datos: LibroUpdate,
    session: AsyncSession = Depends(get_session),
) -> LibroDetalleRead:
    libro = await service.actualizar_libro(session, libro_id, datos)
    return service.detalle(libro)


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
