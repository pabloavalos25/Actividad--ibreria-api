from fastapi import Depends
from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.editoriales.repository import EditorialRepository
from app.modules.generos.repository import GeneroRepository


class LibrosUnitOfWork(UnitOfWork):
    def __init__(self, session):
        super().__init__(session)
        self.libros = LibroRepository(session)
        self.movimientos = MovimientoStockRepository(session)
        self.editoriales = EditorialRepository(session)
        self.generos = GeneroRepository(session)


def get_uow(session=Depends(get_session)):
    return LibrosUnitOfWork(session)
