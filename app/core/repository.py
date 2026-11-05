from datetime import datetime, timezone
from typing import Generic, TypeVar

from sqlalchemy import func, select

from app.core.paginacion import paginar

T = TypeVar('T')


class BaseRepository(Generic[T]):
    def __init__(self, session, model: type[T]):
        self.session = session
        self.model = model

    def query(self):
        return select(self.model)

    async def get_by_id(self, entity_id):
        return await self.session.scalar(self.query().where(self.model.id == entity_id))

    async def get_all(self):
        return list(await self.session.scalars(self.query().order_by(self.model.id)))

    async def count(self):
        return await self.session.scalar(select(func.count()).select_from(self.query().subquery()))

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: T) -> T:
        return await self.add(entity)

    async def delete(self, entity: T):
        await self.session.delete(entity)
        await self.session.flush()

    async def page(self, page, size):
        return await paginar(self.session, self.query().order_by(self.model.id), page, size)


class SoftDeleteRepository(BaseRepository[T]):
    def query(self):
        return super().query().where(self.model.borrado_en.is_(None))

    async def get_by_id_including_deleted(self, entity_id):
        return await self.session.scalar(select(self.model).where(self.model.id == entity_id))

    async def soft_delete(self, entity):
        entity.borrado_en = datetime.now(timezone.utc)
        return await self.update(entity)
