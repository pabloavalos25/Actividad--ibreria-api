from app.core.errors import no_encontrado
from app.modules.generos.models import Genero


async def crear_genero(uow, datos):
    async with uow:
        entity = Genero.model_validate(datos, from_attributes=True)
        await uow.generos.add(entity)
    return entity


async def obtener_genero(uow, genero_id):
    async with uow:
        entity = await uow.generos.get_by_id(genero_id)
        if entity is None:
            raise no_encontrado('Genero no encontrado')
    return entity


async def listar_generos(uow, page, size):
    async with uow:
        return await uow.generos.page(page, size)
