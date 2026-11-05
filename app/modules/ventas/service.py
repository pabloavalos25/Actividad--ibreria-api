from decimal import Decimal
from fastapi import HTTPException
from app.core.errors import no_encontrado
from app.modules.libros.stock import modificar_stock
from app.modules.ventas.models import Venta, RenglonVenta
from app.modules.ventas.schemas import VentaRead, ClienteRef, RenglonRead
from app.modules.usuarios.service import ahora_utc


async def crear_venta(uow, datos, *, usuario_id):
    async with uow:
        if await uow.clientes.get_by_id(datos.cliente_id) is None:
            raise HTTPException(409, 'Cliente inexistente')
        libros = {libro.id: libro for libro in await uow.libros.vigentes_por_ids([r.libro_id for r in datos.renglones])}
        total = Decimal('0')
        renglones = []
        for item in datos.renglones:
            libro = libros.get(item.libro_id)
            if libro is None or libro.stock < item.cantidad:
                raise HTTPException(409, 'Libro no disponible o stock insuficiente')
            total += libro.precio * item.cantidad
            renglones.append(RenglonVenta(libro_id=libro.id, cantidad=item.cantidad, precio_unitario=libro.precio))
        if total > Decimal('9999999999.99'):
            raise HTTPException(422, 'Total fuera de los límites permitidos')
        venta = Venta(cliente_id=datos.cliente_id, total=total, renglones=renglones)
        await uow.ventas.add(venta)
        for item in datos.renglones:
            await modificar_stock(uow, libros[item.libro_id], -item.cantidad, 'Venta', usuario_id, venta.id)
        venta = await uow.ventas.con_cliente_renglones_libros(venta.id)
    return venta


async def listar_ventas(uow, page, size):
    async with uow:
        return await uow.ventas.con_detalles(page, size)


async def obtener_venta(uow, venta_id, usuario_id):
    async with uow:
        venta = await uow.ventas.con_cliente_renglones_libros(venta_id)
        if venta is None:
            raise no_encontrado('Venta no encontrada')
        roles = await uow.usuarios.roles_vigentes(usuario_id, ahora_utc())
        if not set(roles).intersection(('ADMIN','VENDEDOR')) and venta.cliente.usuario_id != usuario_id:
            raise HTTPException(403, 'No tiene permiso para consultar esta venta')
    return venta


async def listar_ventas_de_cliente(uow, cliente_id, page, size):
    async with uow:
        if await uow.clientes.get_by_id(cliente_id) is None:
            raise no_encontrado('Cliente no encontrado')
        return await uow.ventas.con_detalles(page, size, cliente_id=cliente_id)


async def mis_ventas(uow, usuario_id, page, size):
    async with uow:
        return await uow.ventas.con_detalles(page, size, usuario_id=usuario_id)


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
