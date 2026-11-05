from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.editoriales import service
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialRead,
    EditorialUpdate,
)
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroRead

public_router = APIRouter(prefix="/editoriales", tags=["editoriales"])
protected_router = APIRouter(prefix="/editoriales", tags=["editoriales"])



@protected_router.post("/", response_model=EditorialRead, status_code=201, dependencies=[Depends(requiere_admin)])
async def crear_editorial(
    datos: EditorialCreate,
    session: AsyncSession = Depends(get_session),
) -> EditorialRead:
    editorial = await service.crear_editorial(session, datos)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@public_router.get("/", response_model=Pagina[EditorialRead])
async def listar_editoriales(
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session),
) -> dict:
    editoriales = await service.listar_editoriales(session, page, size)
    editoriales["items"] = [EditorialRead.model_validate(e, from_attributes=True) for e in editoriales["items"]]
    return editoriales


@public_router.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(
    editorial_id: Annotated[int, Path(gt=0, le=2147483647)],
    session: AsyncSession = Depends(get_session),
) -> EditorialRead:
    editorial = await service.obtener_editorial(session, editorial_id)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@protected_router.patch("/{editorial_id}", response_model=EditorialRead, dependencies=[Depends(requiere_admin)])
async def actualizar_editorial(
    editorial_id: Annotated[int, Path(gt=0, le=2147483647)],
    datos: EditorialUpdate,
    session: AsyncSession = Depends(get_session),
) -> EditorialRead:
    editorial = await service.actualizar_editorial(session, editorial_id, datos)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@public_router.get("/{editorial_id}/libros", response_model=Pagina[LibroRead])
async def listar_libros_de_editorial(
    editorial_id: Annotated[int, Path(gt=0, le=2147483647)],
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session),
) -> dict:
    libros = await libros_service.listar_libros_de_editorial(
        session, editorial_id, page, size
    )
    libros["items"] = [LibroRead.model_validate(libro, from_attributes=True) for libro in libros["items"]]
    return libros


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
