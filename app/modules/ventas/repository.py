from sqlalchemy.orm import joinedload, selectinload
from app.core.repository import BaseRepository
from app.core.paginacion import paginar
from app.modules.ventas.models import Venta, RenglonVenta
from app.modules.clientes.models import Cliente


class VentaRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, Venta)

    @staticmethod
    def detalle_options():
        return (joinedload(Venta.cliente), selectinload(Venta.renglones).joinedload(RenglonVenta.libro))

    async def con_cliente_renglones_libros(self, venta_id):
        return await self.session.scalar(self.query().where(Venta.id == venta_id)
            .options(*self.detalle_options()).execution_options(populate_existing=True))

    async def con_detalles(self, page, size, cliente_id=None, usuario_id=None):
        query = self.query()
        if cliente_id is not None:
            query = query.where(Venta.cliente_id == cliente_id)
        if usuario_id is not None:
            query = query.join(Cliente).where(Cliente.usuario_id == usuario_id)
        return await paginar(self.session, query.options(*self.detalle_options()).order_by(Venta.id), page, size)
