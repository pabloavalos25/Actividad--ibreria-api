from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import no_encontrado
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate, LibroConRol
from app.modules.libros.models import LibroAutor


async def crear_autor(session: AsyncSession, datos: AutorCreate) -> Autor:
    autor = Autor.model_validate(datos, from_attributes=True)
    session.add(autor)
    await session.commit()
    await session.refresh(autor)
    return autor


async def obtener_autor(session: AsyncSession, autor_id: int) -> Autor:
    result = await session.execute(select(Autor).where(Autor.id == autor_id))
    autor = result.scalar_one_or_none()
    if autor is None:
        raise no_encontrado("Autor no encontrado")
    return autor


async def actualizar_autor(
    session: AsyncSession,
    autor_id: int,
    datos: AutorUpdate,
) -> Autor:
    autor = await obtener_autor(session, autor_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(autor, campo, valor)
    session.add(autor)
    await session.commit()
    await session.refresh(autor)
    return autor


async def listar_libros_de_autor(
    session: AsyncSession,
    autor_id: int,
    limit: int,
    offset: int,
) -> list[LibroConRol]:
    await obtener_autor(session, autor_id)
    result = await session.execute(
        select(LibroAutor)
        .where(LibroAutor.autor_id == autor_id)
        .options(joinedload(LibroAutor.libro))
        .order_by(LibroAutor.orden, LibroAutor.libro_id)
        .offset(offset)
        .limit(limit)
    )
    return [
        LibroConRol(
            libro_id=autoria.libro_id,
            isbn=autoria.libro.isbn,
            titulo=autoria.libro.titulo,
            precio=autoria.libro.precio,
            stock=autoria.libro.stock,
            rol=autoria.rol,
            orden=autoria.orden,
        )
        for autoria in result.scalars().all()
    ]
