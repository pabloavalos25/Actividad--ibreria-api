from app.core.errors import no_encontrado
from app.modules.clientes.models import Cliente


async def crear_cliente(uow, datos):
    async with uow:
        entity = Cliente.model_validate(datos, from_attributes=True)
        await uow.clientes.add(entity)
        entity = await uow.clientes.con_perfil(entity.id)
    return entity


async def obtener_cliente(uow, cliente_id):
    async with uow:
        entity = await uow.clientes.con_perfil(cliente_id)
        if entity is None:
            raise no_encontrado('Cliente no encontrado')
    return entity


async def actualizar_cliente(uow, cliente_id, datos):
    async with uow:
        entity = await uow.clientes.con_perfil(cliente_id)
        if entity is None:
            raise no_encontrado('Cliente no encontrado')
        for field, value in datos.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        await uow.clientes.update(entity)
    return entity


async def crear_perfil(uow, cliente_id, datos):
    from app.modules.clientes.models import PerfilCliente
    async with uow:
        if await uow.clientes.get_by_id(cliente_id) is None:
            raise no_encontrado('Cliente no encontrado')
        perfil = PerfilCliente(**datos.model_dump(), cliente_id=cliente_id)
        await uow.perfiles.add(perfil)
    return perfil


def a_read(cliente):
    from app.modules.clientes.schemas import ClienteRead
    return ClienteRead.model_validate(cliente, from_attributes=True)


def perfil_a_read(perfil):
    from app.modules.clientes.schemas import PerfilRead
    return PerfilRead.model_validate(perfil, from_attributes=True)
