from fastapi import Depends
from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository, PerfilClienteRepository


class ClientesUnitOfWork(UnitOfWork):
    def __init__(self, session):
        super().__init__(session)
        self.clientes = ClienteRepository(session)
        self.perfiles = PerfilClienteRepository(session)


def get_uow(session=Depends(get_session)):
    return ClientesUnitOfWork(session)
