from fastapi import Depends
from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.generos.repository import GeneroRepository


class GenerosUnitOfWork(UnitOfWork):
    def __init__(self, session):
        super().__init__(session)
        self.generos = GeneroRepository(session)


def get_uow(session=Depends(get_session)):
    return GenerosUnitOfWork(session)
