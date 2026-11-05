from sqlalchemy import select
from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente
from sqlalchemy.orm import joinedload
from app.modules.clientes.models import PerfilCliente


class ClienteRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, Cliente)

    async def con_perfil(self, entity_id):
        return await self.session.scalar(self.query().where(Cliente.id == entity_id).options(joinedload(Cliente.perfil)))

    async def por_email(self, email):
        return await self.session.scalar(self.query().where(Cliente.email == email))


class PerfilClienteRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(session, PerfilCliente)
