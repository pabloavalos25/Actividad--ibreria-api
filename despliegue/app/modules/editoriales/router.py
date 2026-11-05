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

router = APIRouter(prefix="/editoriales", tags=["editoriales"])


@router.post("/", response_model=EditorialRead, status_code=201)
async def crear_editorial(
    datos: EditorialCreate,
    session: AsyncSession = Depends(get_session),
) -> EditorialRead:
    editorial = await service.crear_editorial(session, datos)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@router.get("/", response_model=list[EditorialRead])
async def listar_editoriales(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[EditorialRead]:
    editoriales = await service.listar_editoriales(session, limit, offset)
    return [EditorialRead.model_validate(e, from_attributes=True) for e in editoriales]


@router.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(
    editorial_id: int,
    session: AsyncSession = Depends(get_session),
) -> EditorialRead:
    editorial = await service.obtener_editorial(session, editorial_id)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@router.patch("/{editorial_id}", response_model=EditorialRead)
async def actualizar_editorial(
    editorial_id: int,
    datos: EditorialUpdate,
    session: AsyncSession = Depends(get_session),
) -> EditorialRead:
    editorial = await service.actualizar_editorial(session, editorial_id, datos)
    return EditorialRead.model_validate(editorial, from_attributes=True)


@router.get("/{editorial_id}/libros", response_model=list[LibroRead])
async def listar_libros_de_editorial(
    editorial_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[LibroRead]:
    libros = await libros_service.listar_libros_de_editorial(
        session, editorial_id, limit, offset
    )
    return [LibroRead.model_validate(libro, from_attributes=True) for libro in libros]
