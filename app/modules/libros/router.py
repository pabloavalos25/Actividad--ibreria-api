from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
from fastapi import APIRouter, Depends, Query, Response

from app.modules.libros.unit_of_work import get_uow
from app.core.dependencies import requerir_usuario_id
from app.modules.libros import service
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetalleRead,
    LibroRead,
    LibroUpdate,
    ReposicionCreate,
    MovimientoRead,
)

public_router = APIRouter(prefix="/libros", tags=["libros"])
protected_router = APIRouter(prefix="/libros", tags=["libros"])



@protected_router.post("/", response_model=LibroDetalleRead, status_code=201, dependencies=[Depends(requiere_admin)])
async def crear_libro(
    datos: LibroCreate,
    usuario_id: int = Depends(requerir_usuario_id),
    uow = Depends(get_uow),
) -> LibroDetalleRead:
    libro = await service.crear_libro(uow, datos, usuario_id=usuario_id)
    return service.detalle(libro)


@protected_router.delete('/{libro_id}', status_code=204, dependencies=[Depends(requiere_admin)])
async def eliminar_libro(libro_id: Annotated[int, Path(gt=0, le=2147483647)], uow = Depends(get_uow)) -> Response:
    await service.eliminar_libro(uow, libro_id)
    return Response(status_code=204)


@public_router.get("/", response_model=Pagina[LibroRead])
async def listar_libros(
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    titulo: str | None = Query(None),
    genero_id: int | None = Query(None, gt=0, le=2147483647),
    uow = Depends(get_uow),
) -> dict:
    libros = await service.listar_libros(
        uow, page, size, titulo, genero_id
    )
    libros["items"] = [LibroRead.model_validate(libro, from_attributes=True) for libro in libros["items"]]
    return libros


@public_router.get("/{libro_id}", response_model=LibroDetalleRead)
async def obtener_libro(
    libro_id: Annotated[int, Path(gt=0, le=2147483647)],
    uow = Depends(get_uow),
) -> LibroDetalleRead:
    libro = await service.obtener_libro(uow, libro_id)
    return service.detalle(libro)


@protected_router.patch("/{libro_id}", response_model=LibroDetalleRead, dependencies=[Depends(requiere_admin)])
async def actualizar_libro(
    libro_id: Annotated[int, Path(gt=0, le=2147483647)],
    datos: LibroUpdate,
    uow = Depends(get_uow),
) -> LibroDetalleRead:
    libro = await service.actualizar_libro(uow, libro_id, datos)
    return service.detalle(libro)


@protected_router.post('/{libro_id}/reponer', response_model=LibroDetalleRead, dependencies=[Depends(requiere_admin)])
async def reponer(libro_id: Annotated[int, Path(gt=0, le=2147483647)], datos: ReposicionCreate,
                  usuario_id: int = Depends(requerir_usuario_id), uow=Depends(get_uow)):
    return service.detalle(await service.reponer(uow, libro_id, datos, usuario_id))


@protected_router.get('/{libro_id}/movimientos', response_model=Pagina[MovimientoRead], dependencies=[Depends(requiere_admin)])
async def movimientos(libro_id: Annotated[int, Path(gt=0, le=2147483647)], page: int = Query(1, ge=1),
                      size: int = Query(20, ge=1, le=100), uow=Depends(get_uow)):
    return await service.listar_movimientos(uow, libro_id, page, size)


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
