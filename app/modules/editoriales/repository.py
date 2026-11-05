from sqlalchemy import select
from app.core.repository import BaseRepository
from app.modules.editoriales.models import Editorial


class EditorialRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, Editorial)
