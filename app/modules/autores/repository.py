from sqlalchemy import select
from app.core.repository import BaseRepository
from app.modules.autores.models import Autor
from sqlalchemy.orm import joinedload
from app.modules.libros.models import Libro, LibroAutor
from app.core.paginacion import paginar


class AutorRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, Autor)

    async def libros_con_autoria(self, autor_id, page, size):
        return await paginar(self.session, select(LibroAutor).join(Libro)
            .where(LibroAutor.autor_id == autor_id, Libro.borrado_en.is_(None))
            .options(joinedload(LibroAutor.libro)).order_by(LibroAutor.orden, LibroAutor.libro_id), page, size)
