from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflicto_de_integridad, no_encontrado
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate


async def crear_genero(session: AsyncSession, datos: GeneroCreate) -> Genero:
    genero = Genero.model_validate(datos, from_attributes=True)
    session.add(genero)
    async with conflicto_de_integridad(
        session, "Ya existe un genero con ese nombre"
    ):
        await session.commit()
    await session.refresh(genero)
    return genero


async def listar_generos(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> list[Genero]:
    result = await session.execute(
        select(Genero).order_by(Genero.id).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def obtener_genero(session: AsyncSession, genero_id: int) -> Genero:
    result = await session.execute(select(Genero).where(Genero.id == genero_id))
    genero = result.scalar_one_or_none()
    if genero is None:
        raise no_encontrado("Genero no encontrado")
    return genero
