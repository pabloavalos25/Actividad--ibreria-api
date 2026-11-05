from app.core.errors import no_encontrado
from app.modules.autores.models import Autor


async def crear_autor(uow, datos):
    async with uow:
        entity = Autor.model_validate(datos, from_attributes=True)
        await uow.autores.add(entity)
    return entity


async def obtener_autor(uow, autor_id):
    async with uow:
        entity = await uow.autores.get_by_id(autor_id)
        if entity is None:
            raise no_encontrado('Autor no encontrado')
    return entity


async def actualizar_autor(uow, autor_id, datos):
    async with uow:
        entity = await uow.autores.get_by_id(autor_id)
        if entity is None:
            raise no_encontrado('Autor no encontrado')
        for field, value in datos.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await uow.autores.update(entity)
    return entity


async def listar_libros_de_autor(uow, autor_id, page, size):
    from app.modules.autores.schemas import LibroConRol
    async with uow:
        if await uow.autores.get_by_id(autor_id) is None:
            raise no_encontrado('Autor no encontrado')
        pagina = await uow.autores.libros_con_autoria(autor_id, page, size)
        pagina['items'] = [LibroConRol(libro_id=a.libro_id, isbn=a.libro.isbn,
            titulo=a.libro.titulo, precio=a.libro.precio, stock=a.libro.stock,
            rol=a.rol, orden=a.orden) for a in pagina['items']]
        return pagina
