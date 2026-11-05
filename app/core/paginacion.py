from typing import Generic, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

T = TypeVar('T')


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


async def paginar(session, consulta, page: int, size: int) -> dict:
    if page < 1 or not 1 <= size <= 100:
        raise HTTPException(422, 'Parámetros de paginación inválidos')
    total = await session.scalar(select(func.count()).select_from(
        consulta.order_by(None).subquery()
    ))
    pages = max(1, (total + size - 1) // size)
    if page > pages:
        raise HTTPException(422, 'Página fuera de rango')
    resultado = await session.execute(consulta.offset((page - 1) * size).limit(size))
    return dict(items=list(resultado.scalars().unique().all()), total=total,
                page=page, size=size, pages=pages)
