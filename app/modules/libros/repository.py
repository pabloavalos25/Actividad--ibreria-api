from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.core.paginacion import paginar
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock


class LibroRepository(SoftDeleteRepository):
    def __init__(self, session):
        super().__init__(session, Libro)

    @staticmethod
    def detalle_options():
        return (joinedload(Libro.editorial), joinedload(Libro.genero),
                selectinload(Libro.autorias).joinedload(LibroAutor.autor))

    async def con_detalle(self, libro_id):
        return await self.session.scalar(self.query().where(Libro.id == libro_id)
            .options(*self.detalle_options()).execution_options(populate_existing=True))

    async def catalogo(self, page, size, titulo=None, genero_id=None, editorial_id=None):
        query = self.query()
        if titulo is not None:
            query = query.where(Libro.titulo.ilike(f'%{titulo}%'))
        if genero_id is not None:
            query = query.where(Libro.genero_id == genero_id)
        if editorial_id is not None:
            query = query.where(Libro.editorial_id == editorial_id)
        return await paginar(self.session, query.options(joinedload(Libro.editorial),
            joinedload(Libro.genero)).order_by(Libro.id), page, size)

    async def vigentes_por_ids(self, ids):
        return list(await self.session.scalars(self.query().where(Libro.id.in_(ids))))


class MovimientoStockRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, MovimientoStock)

    async def de_libro(self, libro_id, page, size):
        return await paginar(self.session, self.query().where(MovimientoStock.libro_id == libro_id)
            .order_by(MovimientoStock.id), page, size)
