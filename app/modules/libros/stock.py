from fastapi import HTTPException
from app.modules.libros.models import MovimientoStock


async def modificar_stock(uow, libro, cantidad, motivo, usuario_id, venta_id=None):
    """Punto único de escritura de existencias dentro del UoW del llamador."""
    if cantidad == 0:
        return
    if libro.borrado_en is not None:
        raise HTTPException(409, 'El libro está dado de baja')
    nuevo = libro.stock + cantidad
    if nuevo < 0:
        raise HTTPException(409, 'Stock insuficiente')
    if nuevo > 2147483647:
        raise HTTPException(422, 'Stock fuera de los límites permitidos')
    libro.stock = nuevo
    await uow.libros.update(libro)
    await uow.movimientos.add(MovimientoStock(libro_id=libro.id, usuario_id=usuario_id,
        cantidad=cantidad, motivo=motivo, venta_id=venta_id))
