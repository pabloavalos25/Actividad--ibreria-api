from fastapi import APIRouter, Depends, Request, Response
from app.core.dependencies import get_uow, get_sesion_actual
from app.core.security import create_token
from app.modules.usuarios import service
from app.modules.usuarios.schemas import Registro, Login, CambiarPassword, UsuarioRead, LoginRead, SesionRead

router = APIRouter(prefix='/auth', tags=['acceso'])


@router.post('/registro', response_model=UsuarioRead, status_code=201)
async def registro(datos: Registro, request: Request, uow=Depends(get_uow)):
    return await service.registrar(uow, datos, request.app.state.settings, request.app.state.bcrypt_semaphore)


@router.post('/login', response_model=LoginRead)
async def login(datos: Login, request: Request, response: Response, uow=Depends(get_uow)):
    state = request.app.state
    usuario, roles = await service.login(uow, datos, state.session_factory, state.dummy_password_hash,
                                        state.bcrypt_semaphore, request.client.host if request.client else 'desconocida')
    settings = state.settings
    token = create_token(usuario.id, roles, secret=settings.jwt_secret.get_secret_value(), ttl=settings.jwt_ttl_seconds)
    response.set_cookie('access_token', token, max_age=settings.jwt_ttl_seconds,
                        httponly=True, samesite='lax', secure=settings.cookie_secure)
    return LoginRead(mensaje='Sesión iniciada', debe_cambiar_password=usuario.debe_cambiar_password,
                     expira_en_segundos=settings.jwt_ttl_seconds)


@router.post('/logout')
async def logout(request: Request, response: Response):
    response.delete_cookie('access_token', httponly=True, samesite='lax', secure=request.app.state.settings.cookie_secure)
    return {'mensaje': 'Sesión cerrada'}


@router.get('/yo', response_model=SesionRead)
async def yo(actual=Depends(get_sesion_actual), uow=Depends(get_uow)):
    usuario, claims = actual
    roles = await uow.usuarios.roles_vigentes(usuario.id, service.ahora_utc())
    return SesionRead(usuario=UsuarioRead.model_validate(usuario), roles_vigentes=roles, roles_token=claims['roles'])


@router.post('/cambiar-password')
async def cambiar_password(datos: CambiarPassword, request: Request, actual=Depends(get_sesion_actual), uow=Depends(get_uow)):
    await service.cambiar_password(uow, actual[0], datos, request.app.state.settings, request.app.state.bcrypt_semaphore)
    return {'mensaje': 'Contraseña actualizada'}
