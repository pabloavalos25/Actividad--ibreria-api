from fastapi import Depends
from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.ventas.repository import VentaRepository
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.repository import UsuarioRepository


class VentasUnitOfWork(UnitOfWork):
    def __init__(self, session):
        super().__init__(session)
        self.ventas = VentaRepository(session)
        self.libros = LibroRepository(session)
        self.movimientos = MovimientoStockRepository(session)
        self.clientes = ClienteRepository(session)
        self.usuarios = UsuarioRepository(session)


def get_uow(session=Depends(get_session)):
    return VentasUnitOfWork(session)
