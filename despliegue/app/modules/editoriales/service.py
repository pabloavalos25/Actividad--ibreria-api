from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflicto_de_integridad, no_encontrado
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate


async def crear_editorial(
    session: AsyncSession,
    datos: EditorialCreate,
) -> Editorial:
    editorial = Editorial.model_validate(datos, from_attributes=True)
    session.add(editorial)
    async with conflicto_de_integridad(
        session, "Ya existe una editorial con ese nombre"
    ):
        await session.commit()
    await session.refresh(editorial)
    return editorial


async def listar_editoriales(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> list[Editorial]:
    result = await session.execute(
        select(Editorial).order_by(Editorial.id).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def obtener_editorial(session: AsyncSession, editorial_id: int) -> Editorial:
    result = await session.execute(
        select(Editorial).where(Editorial.id == editorial_id)
    )
    editorial = result.scalar_one_or_none()
    if editorial is None:
        raise no_encontrado("Editorial no encontrada")
    return editorial


async def actualizar_editorial(
    session: AsyncSession,
    editorial_id: int,
    datos: EditorialUpdate,
) -> Editorial:
    editorial = await obtener_editorial(session, editorial_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(editorial, campo, valor)
    session.add(editorial)
    async with conflicto_de_integridad(
        session, "Ya existe una editorial con ese nombre"
    ):
        await session.commit()
    await session.refresh(editorial)
    return editorial
