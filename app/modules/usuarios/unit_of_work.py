from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.modules.usuarios.repository import UsuarioRepository


class UsuariosUnitOfWork:
    def __init__(self, session):
        self.session = session
        self.usuarios = UsuarioRepository(session)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        except Exception:
            await self.session.rollback()
            raise
        if isinstance(exc, IntegrityError):
            raise HTTPException(409, 'El correo ya está registrado') from exc
