from datetime import datetime
from sqlalchemy import select, func
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

    async def historial_roles(self, usuario_id):
        return list(await self.session.scalars(select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id).order_by(AsignacionRol.id)))

    async def rol_abierto(self, usuario_id, rol):
        return await self.session.scalar(select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id, AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None)))

    async def cantidad_admin(self, ahora, excluir=None):
        consulta = select(func.count()).select_from(AsignacionRol).join(Usuario, Usuario.id == AsignacionRol.usuario_id).where(
            Usuario.activo.is_(True), AsignacionRol.rol == 'ADMIN',
            AsignacionRol.revocada_en.is_(None), AsignacionRol.desde <= ahora,
            AsignacionRol.vence_en.is_(None) | (AsignacionRol.vence_en > ahora))
        if excluir is not None:
            consulta = consulta.where(AsignacionRol.usuario_id != excluir)
        return await self.session.scalar(consulta)
