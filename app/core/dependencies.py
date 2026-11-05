from fastapi import Depends, HTTPException, Request
import jwt
from app.core.database import get_session
from app.core.security import decode_token
from app.modules.usuarios.repository import UsuarioRepository
from app.modules.usuarios.service import ahora_utc
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork


async def get_uow(session=Depends(get_session)):
    return UsuariosUnitOfWork(session)


async def get_sesion_actual(request: Request, session=Depends(get_session)):
    token = request.cookies.get('access_token')
    if not token:
        raise HTTPException(401, 'Se requiere una sesión autenticada')
    try:
        claims = decode_token(token, secret=request.app.state.settings.jwt_secret.get_secret_value())
    except jwt.InvalidTokenError:
        raise HTTPException(401, 'Sesión inválida o vencida') from None
    usuario = await UsuarioRepository(session).por_id(int(claims['sub']))
    if not usuario or not usuario.activo:
        raise HTTPException(401, 'Sesión inválida o vencida')
    return usuario, claims


async def get_usuario_actual(actual=Depends(get_sesion_actual)):
    return actual[0]


def requiere_rol(*permitidos):
    async def comprobar(usuario=Depends(get_usuario_actual), session=Depends(get_session)):
        roles = await UsuarioRepository(session).roles_vigentes(usuario.id, ahora_utc())
        if not set(roles).intersection(permitidos):
            raise HTTPException(403, 'No tiene permiso para realizar esta operación')
        return usuario
    return comprobar


requiere_admin = requiere_rol('ADMIN')
requiere_personal = requiere_rol('ADMIN', 'VENDEDOR')


async def verificar_cambio_obligatorio(usuario=Depends(get_usuario_actual)):
    if usuario.debe_cambiar_password:
        raise HTTPException(403, 'Debe cambiar su contraseña')


async def requerir_usuario_id(usuario=Depends(requiere_admin)) -> int:
    return usuario.id
