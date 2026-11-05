from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def conflicto_de_integridad(
    session: AsyncSession,
    mensaje: str,
) -> AsyncIterator[None]:
    try:
        yield
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=mensaje) from exc
    except DataError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail='Datos fuera de los límites permitidos') from exc


def no_encontrado(mensaje: str) -> HTTPException:
    return HTTPException(status_code=404, detail=mensaje)
