from fastapi import HTTPException
from sqlalchemy.exc import DataError, IntegrityError


class UnitOfWork:
    """Adopta también autobegin de lecturas; la petición conserva la sesión."""

    def __init__(self, session, conflict_message='La operación entra en conflicto con los datos guardados'):
        self.session = session
        self.conflict_message = conflict_message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        except Exception as commit_error:
            await self.session.rollback()
            self._translate(commit_error)
            raise
        if exc is not None:
            self._translate(exc)

    def _translate(self, error):
        if isinstance(error, IntegrityError):
            raise HTTPException(409, self.conflict_message) from error
        if isinstance(error, DataError):
            raise HTTPException(422, 'Datos fuera de los límites permitidos') from error

    async def terminar_lectura(self):
        """Cerrar la lectura de autenticación antes de bcrypt, sin datos pendientes."""
        if self.session.new or self.session.dirty or self.session.deleted:
            raise RuntimeError('No se puede descartar una transacción con cambios pendientes')
        await self.session.rollback()
