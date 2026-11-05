from app.core.errors import no_encontrado
from app.modules.editoriales.models import Editorial


async def crear_editorial(uow, datos):
    async with uow:
        entity = Editorial.model_validate(datos, from_attributes=True)
        await uow.editoriales.add(entity)
    return entity


async def obtener_editorial(uow, editorial_id):
    async with uow:
        entity = await uow.editoriales.get_by_id(editorial_id)
        if entity is None:
            raise no_encontrado('Editorial no encontrada')
    return entity


async def listar_editoriales(uow, page, size):
    async with uow:
        return await uow.editoriales.page(page, size)


async def actualizar_editorial(uow, editorial_id, datos):
    async with uow:
        entity = await uow.editoriales.get_by_id(editorial_id)
        if entity is None:
            raise no_encontrado('Editorial no encontrada')
        for field, value in datos.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await uow.editoriales.update(entity)
    return entity
