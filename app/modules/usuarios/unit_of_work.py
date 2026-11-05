from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.repository import UsuarioRepository
from app.modules.usuarios.repository import AsignacionRolRepository, EventoSeguridadRepository
from app.modules.clientes.repository import ClienteRepository


class UsuariosUnitOfWork(UnitOfWork):
    def __init__(self, session):
        super().__init__(session, 'El correo o la asignación ya están registrados')
        self.usuarios = UsuarioRepository(session)
        self.roles = AsignacionRolRepository(session)
        self.eventos = EventoSeguridadRepository(session)
        self.clientes = ClienteRepository(session)
