from fastapi import HTTPException
from app.core.errors import no_encontrado
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import LibroDetalleRead, LibroRead, AutorConRol
from app.modules.libros.stock import modificar_stock


async def crear_libro(uow, datos, *, usuario_id):
    async with uow:
        libro = Libro(isbn=datos.isbn, titulo=datos.titulo, precio=datos.precio,
            stock=0, editorial_id=datos.editorial_id, genero_id=datos.genero_id,
            autorias=[LibroAutor(autor_id=a.autor_id, rol=a.rol, orden=a.orden) for a in datos.autores])
        await uow.libros.add(libro)
        await modificar_stock(uow, libro, datos.stock_inicial, 'Stock inicial', usuario_id)
        libro = await uow.libros.con_detalle(libro.id)
    return libro


async def listar_libros(uow, page, size, titulo, genero_id):
    async with uow:
        return await uow.libros.catalogo(page, size, titulo=titulo, genero_id=genero_id)


async def obtener_libro(uow, libro_id):
    async with uow:
        libro = await uow.libros.con_detalle(libro_id)
        if libro is None:
            raise no_encontrado('Libro no encontrado')
    return libro


async def eliminar_libro(uow, libro_id):
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if libro is None:
            raise no_encontrado('Libro no encontrado')
        await uow.libros.soft_delete(libro)


async def actualizar_libro(uow, libro_id, datos):
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if libro is None:
            raise no_encontrado('Libro no encontrado')
        for field, value in datos.model_dump(exclude_unset=True).items():
            setattr(libro, field, value)
        await uow.libros.update(libro)
        libro = await uow.libros.con_detalle(libro_id)
    return libro


async def listar_libros_de_editorial(uow, editorial_id, page, size):
    async with uow:
        if await uow.editoriales.get_by_id(editorial_id) is None:
            raise no_encontrado('Editorial no encontrada')
        return await uow.libros.catalogo(page, size, editorial_id=editorial_id)


async def listar_libros_de_genero(uow, genero_id, page, size):
    async with uow:
        if await uow.generos.get_by_id(genero_id) is None:
            raise no_encontrado('Genero no encontrado')
        return await uow.libros.catalogo(page, size, genero_id=genero_id)


async def reponer(uow, libro_id, datos, usuario_id):
    async with uow:
        libro = await uow.libros.get_by_id_including_deleted(libro_id)
        if libro is None:
            raise no_encontrado('Libro no encontrado')
        await modificar_stock(uow, libro, datos.cantidad, datos.motivo, usuario_id)
        libro = await uow.libros.con_detalle(libro_id)
    return libro


async def listar_movimientos(uow, libro_id, page, size):
    async with uow:
        if await uow.libros.get_by_id_including_deleted(libro_id) is None:
            raise no_encontrado('Libro no encontrado')
        return await uow.movimientos.de_libro(libro_id, page, size)


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
