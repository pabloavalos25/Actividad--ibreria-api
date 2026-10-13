from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.errors import conflicto_de_integridad, no_encontrado
from app.modules.clientes import service as clientes_service
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import (
    ClienteRef,
    RenglonRead,
    VentaCreate,
    VentaRead,
)

opciones_venta = (
    joinedload(Venta.cliente),
    selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
)


async def crear_venta(session: AsyncSession, datos: VentaCreate) -> Venta:
    libro_ids = [r.libro_id for r in datos.renglones]
    result = await session.execute(
        select(Libro).where(Libro.id.in_(libro_ids))
    )
    libros = {libro.id: libro for libro in result.scalars().all()}

    total = Decimal("0")
    renglones: list[RenglonVenta] = []
    for item in datos.renglones:
        libro = libros.get(item.libro_id)
        if libro is None:
            raise HTTPException(
                status_code=409,
                detail="No se pudo registrar la venta: cliente o libros invalidos",
            )
        total += libro.precio * item.cantidad
        renglones.append(
            RenglonVenta(
                libro_id=item.libro_id,
                cantidad=item.cantidad,
                precio_unitario=libro.precio,
            )
        )

    venta = Venta(cliente_id=datos.cliente_id, total=total, renglones=renglones)
    session.add(venta)
    async with conflicto_de_integridad(
        session, "No se pudo registrar la venta: cliente o libros invalidos"
    ):
        await session.commit()
    return await obtener_venta(session, venta.id)


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
    limit: int,
    offset: int,
) -> list[Venta]:
    await clientes_service.obtener_cliente(session, cliente_id)
    result = await session.execute(
        select(Venta)
        .where(Venta.cliente_id == cliente_id)
        .options(*opciones_venta)
        .order_by(Venta.id)
        .offset(offset)
        .limit(limit)
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
