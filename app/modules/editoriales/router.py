from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
from fastapi import APIRouter, Depends, Query

from app.modules.editoriales.unit_of_work import get_uow
from app.modules.editoriales import service
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialRead,
    EditorialUpdate,
)
from app.modules.libros import service as libros_service
from app.modules.libros.unit_of_work import get_uow as get_libros_uow
from app.modules.libros.schemas import LibroRead

public_router = APIRouter(prefix="/editoriales", tags=["editoriales"])
protected_router = APIRouter(prefix="/editoriales", tags=["editoriales"])



@protected_router.post("/", response_model=EditorialRead, status_code=201, dependencies=[Depends(requiere_admin)])
async def crear_editorial(
    datos: EditorialCreate,
    uow = Depends(get_uow),
) -> EditorialRead:
    editorial = await service.crear_editorial(uow, datos)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@public_router.get("/", response_model=Pagina[EditorialRead])
async def listar_editoriales(
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    uow = Depends(get_uow),
) -> dict:
    editoriales = await service.listar_editoriales(uow, page, size)
    editoriales["items"] = [EditorialRead.model_validate(e, from_attributes=True) for e in editoriales["items"]]
    return editoriales


@public_router.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(
    editorial_id: Annotated[int, Path(gt=0, le=2147483647)],
    uow = Depends(get_uow),
) -> EditorialRead:
    editorial = await service.obtener_editorial(uow, editorial_id)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@protected_router.patch("/{editorial_id}", response_model=EditorialRead, dependencies=[Depends(requiere_admin)])
async def actualizar_editorial(
    editorial_id: Annotated[int, Path(gt=0, le=2147483647)],
    datos: EditorialUpdate,
    uow = Depends(get_uow),
) -> EditorialRead:
    editorial = await service.actualizar_editorial(uow, editorial_id, datos)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@public_router.get("/{editorial_id}/libros", response_model=Pagina[LibroRead])
async def listar_libros_de_editorial(
    editorial_id: Annotated[int, Path(gt=0, le=2147483647)],
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    uow = Depends(get_libros_uow),
) -> dict:
    libros = await libros_service.listar_libros_de_editorial(
        uow, editorial_id, page, size
    )
    libros["items"] = [LibroRead.model_validate(libro, from_attributes=True) for libro in libros["items"]]
    return libros


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
