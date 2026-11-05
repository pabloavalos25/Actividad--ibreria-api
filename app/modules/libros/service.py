from app.core.paginacion import paginar
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.errors import conflicto_de_integridad, no_encontrado
from app.modules.editoriales import service as editoriales_service
from app.modules.generos import service as generos_service
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
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


async def crear_libro(session: AsyncSession, datos: LibroCreate, *, usuario_id: int) -> Libro:
    libro = Libro(
        isbn=datos.isbn,
        titulo=datos.titulo,
        precio=datos.precio,
        stock=datos.stock_inicial,
        editorial_id=datos.editorial_id,
        genero_id=datos.genero_id,
        autorias=[
            LibroAutor(autor_id=a.autor_id, rol=a.rol, orden=a.orden)
            for a in datos.autores
        ],
    )
    session.add(libro)
    async with conflicto_de_integridad(
        session, "No se pudo crear el libro: editorial, genero, autor o isbn invalidos"
    ):
        if datos.stock_inicial:
            session.add(MovimientoStock(libro=libro, usuario_id=usuario_id,
                                        cantidad=datos.stock_inicial, motivo='Stock inicial'))
        await session.commit()
    return await obtener_libro(session, libro.id)


async def listar_libros(
    session: AsyncSession,
    page: int,
    size: int,
    titulo: str | None,
    genero_id: int | None,
) -> dict:
    consulta = select(Libro).where(Libro.borrado_en.is_(None))
    if titulo is not None:
        consulta = consulta.where(Libro.titulo.ilike(f"%{titulo}%"))
    if genero_id is not None:
        consulta = consulta.where(Libro.genero_id == genero_id, Libro.borrado_en.is_(None))
    consulta = (
        consulta.options(*opciones_listado)
        .order_by(Libro.id)
    )
    return await paginar(session, consulta, page, size)


async def obtener_libro(session: AsyncSession, libro_id: int) -> Libro:
    result = await session.execute(
        select(Libro)
        .where(Libro.id == libro_id, Libro.borrado_en.is_(None))
        .options(*opciones_detalle)
    )
    libro = result.scalar_one_or_none()
    if libro is None:
        raise no_encontrado("Libro no encontrado")
    return libro


async def eliminar_libro(session: AsyncSession, libro_id: int) -> None:
    libro = await obtener_libro(session, libro_id)
    libro.borrado_en = datetime.now(timezone.utc)
    await session.commit()


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
    page: int,
    size: int,
) -> dict:
    await editoriales_service.obtener_editorial(session, editorial_id)
    pagina = await paginar(
        session,
        select(Libro)
        .where(Libro.editorial_id == editorial_id, Libro.borrado_en.is_(None))
        .options(*opciones_listado)
        .order_by(Libro.id),
        page,
        size,
    )
    return pagina


async def listar_libros_de_genero(
    session: AsyncSession,
    genero_id: int,
    page: int,
    size: int,
) -> dict:
    await generos_service.obtener_genero(session, genero_id)
    pagina = await paginar(
        session,
        select(Libro)
        .where(Libro.genero_id == genero_id, Libro.borrado_en.is_(None))
        .options(*opciones_listado)
        .order_by(Libro.id),
        page,
        size,
    )
    return pagina


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
