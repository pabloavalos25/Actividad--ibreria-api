from sqlalchemy import select
from app.core.repository import BaseRepository
from app.modules.generos.models import Genero


class GeneroRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, Genero)
