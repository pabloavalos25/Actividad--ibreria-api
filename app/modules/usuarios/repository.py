from datetime import datetime
from sqlalchemy import select
from app.modules.usuarios.models import Usuario, AsignacionRol
from app.modules.clientes.models import Cliente


class UsuarioRepository:
    def __init__(self, session):
        self.session = session

    async def por_email(self, email):
        return await self.session.scalar(select(Usuario).where(Usuario.email == email))

    async def por_id(self, usuario_id):
        return await self.session.get(Usuario, usuario_id)

    async def cliente_por_email(self, email):
        return await self.session.scalar(select(Cliente).where(Cliente.email == email))

    async def roles_vigentes(self, usuario_id: int, ahora: datetime) -> list[str]:
        result = await self.session.scalars(select(AsignacionRol.rol).where(
            AsignacionRol.usuario_id == usuario_id, AsignacionRol.revocada_en.is_(None),
            AsignacionRol.desde <= ahora,
            (AsignacionRol.vence_en.is_(None) | (AsignacionRol.vence_en > ahora)),
        ).order_by(AsignacionRol.rol))
        return list(result)

    async def add(self, entity):
        self.session.add(entity)
        await self.session.flush()
