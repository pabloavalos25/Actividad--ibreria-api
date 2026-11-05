from fastapi import Depends
from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.autores.repository import AutorRepository


class AutoresUnitOfWork(UnitOfWork):
    def __init__(self, session):
        super().__init__(session)
        self.autores = AutorRepository(session)


def get_uow(session=Depends(get_session)):
    return AutoresUnitOfWork(session)
