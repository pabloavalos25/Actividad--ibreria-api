from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.errors import conflicto_de_integridad, no_encontrado
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)


async def crear_cliente(session: AsyncSession, datos: ClienteCreate) -> Cliente:
    cliente = Cliente.model_validate(datos, from_attributes=True)
    session.add(cliente)
    async with conflicto_de_integridad(session, "Ya existe un cliente con ese email"):
        await session.commit()
    return await obtener_cliente(session, cliente.id)


async def obtener_cliente(session: AsyncSession, cliente_id: int) -> Cliente:
    result = await session.execute(
        select(Cliente)
        .where(Cliente.id == cliente_id)
        .options(joinedload(Cliente.perfil))
    )
    cliente = result.scalar_one_or_none()
    if cliente is None:
        raise no_encontrado("Cliente no encontrado")
    return cliente


async def actualizar_cliente(
    session: AsyncSession,
    cliente_id: int,
    datos: ClienteUpdate,
) -> Cliente:
    cliente = await obtener_cliente(session, cliente_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    session.add(cliente)
    async with conflicto_de_integridad(
        session, "Ya existe un cliente con ese email"
    ):
        await session.commit()
    return await obtener_cliente(session, cliente_id)


async def crear_perfil(
    session: AsyncSession,
    cliente_id: int,
    datos: PerfilCreate,
) -> PerfilCliente:
    await obtener_cliente(session, cliente_id)
    perfil = PerfilCliente.model_validate(
        {**datos.model_dump(), "cliente_id": cliente_id},
        from_attributes=True,
    )
    session.add(perfil)
    async with conflicto_de_integridad(
        session, "El cliente ya tiene un perfil"
    ):
        await session.commit()
    await session.refresh(perfil)
    return perfil


def a_read(cliente: Cliente) -> ClienteRead:
    return ClienteRead.model_validate(cliente, from_attributes=True)


def perfil_a_read(perfil: PerfilCliente) -> PerfilRead:
    return PerfilRead.model_validate(perfil, from_attributes=True)
