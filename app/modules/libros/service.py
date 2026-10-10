from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.errors import conflicto_de_integridad, no_encontrado
from app.modules.editoriales import service as editoriales_service
from app.modules.generos import service as generos_service
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import (
    AutorConRol,
    LibroCreate,
    LibroDetalleRead,
    LibroRead,
    LibroUpdate,
)

opciones_detalle = (
    joinedload(Libro.editorial),
    joinedload(Libro.genero),
    selectinload(Libro.autorias).joinedload(LibroAutor.autor),
)

opciones_listado = (
    joinedload(Libro.editorial),
    joinedload(Libro.genero),
)


async def crear_libro(session: AsyncSession, datos: LibroCreate) -> Libro:
    libro = Libro.model_validate(datos, from_attributes=True)
    session.add(libro)
    async with conflicto_de_integridad(
        session, "No se pudo crear el libro: editorial, genero o isbn invalidos"
    ):
        await session.commit()
    await session.refresh(libro)
    return libro


async def listar_libros(
    session: AsyncSession,
    limit: int,
    offset: int,
    titulo: str | None,
    genero_id: int | None,
) -> list[Libro]:
    consulta = select(Libro)
    if titulo is not None:
        consulta = consulta.where(Libro.titulo.ilike(f"%{titulo}%"))
    if genero_id is not None:
        consulta = consulta.where(Libro.genero_id == genero_id)
    consulta = (
        consulta.options(*opciones_listado)
        .order_by(Libro.id)
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(consulta)
    return list(result.scalars().unique().all())


async def obtener_libro(session: AsyncSession, libro_id: int) -> Libro:
    result = await session.execute(
        select(Libro)
        .where(Libro.id == libro_id)
        .options(*opciones_detalle)
    )
    libro = result.scalar_one_or_none()
    if libro is None:
        raise no_encontrado("Libro no encontrado")
    return libro


async def actualizar_libro(
    session: AsyncSession,
    libro_id: int,
    datos: LibroUpdate,
) -> Libro:
    libro = await obtener_libro(session, libro_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(libro, campo, valor)
    session.add(libro)
    async with conflicto_de_integridad(
        session, "No se pudo actualizar el libro: editorial, genero o isbn invalidos"
    ):
        await session.commit()
    return await obtener_libro(session, libro_id)


async def listar_libros_de_editorial(
    session: AsyncSession,
    editorial_id: int,
) -> list[Libro]:
    await editoriales_service.obtener_editorial(session, editorial_id)
    result = await session.execute(
        select(Libro)
        .where(Libro.editorial_id == editorial_id)
        .options(*opciones_listado)
        .order_by(Libro.id)
    )
    return list(result.scalars().unique().all())


async def listar_libros_de_genero(
    session: AsyncSession,
    genero_id: int,
) -> list[Libro]:
    await generos_service.obtener_genero(session, genero_id)
    result = await session.execute(
        select(Libro)
        .where(Libro.genero_id == genero_id)
        .options(*opciones_listado)
        .order_by(Libro.id)
    )
    return list(result.scalars().unique().all())


def detalle(libro: Libro) -> LibroDetalleRead:
    resumen = LibroRead.model_validate(libro, from_attributes=True)
    autores = [
        AutorConRol(
            autor_id=autoria.autor.id,
            nombre=autoria.autor.nombre,
            rol=autoria.rol,
            orden=autoria.orden,
        )
        for autoria in libro.autorias
    ]
    return LibroDetalleRead(**resumen.model_dump(), autores=autores)
