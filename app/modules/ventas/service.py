from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.errors import no_encontrado
from app.modules.clientes import service as clientes_service
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import ClienteRef, RenglonRead, VentaRead

opciones_venta = (
    joinedload(Venta.cliente),
    selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
)


async def listar_ventas(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> list[Venta]:
    result = await session.execute(
        select(Venta)
        .options(*opciones_venta)
        .order_by(Venta.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().unique().all())


async def obtener_venta(session: AsyncSession, venta_id: int) -> Venta:
    result = await session.execute(
        select(Venta)
        .where(Venta.id == venta_id)
        .options(*opciones_venta)
    )
    venta = result.scalar_one_or_none()
    if venta is None:
        raise no_encontrado("Venta no encontrada")
    return venta


async def listar_ventas_de_cliente(
    session: AsyncSession,
    cliente_id: int,
) -> list[Venta]:
    await clientes_service.obtener_cliente(session, cliente_id)
    result = await session.execute(
        select(Venta)
        .where(Venta.cliente_id == cliente_id)
        .options(*opciones_venta)
        .order_by(Venta.id)
    )
    return list(result.scalars().unique().all())


def a_read(venta: Venta) -> VentaRead:
    return VentaRead(
        id=venta.id,
        fecha=venta.fecha,
        total=venta.total,
        cliente=ClienteRef.model_validate(venta.cliente, from_attributes=True),
        renglones=[
            RenglonRead(
                libro_id=renglon.libro_id,
                titulo=renglon.libro.titulo,
                cantidad=renglon.cantidad,
                precio_unitario=renglon.precio_unitario,
            )
            for renglon in sorted(venta.renglones, key=lambda r: r.id)
        ],
    )
