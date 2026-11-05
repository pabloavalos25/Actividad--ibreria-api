from datetime import datetime, timedelta, timezone
from math import ceil
from fastapi import HTTPException
from sqlalchemy import select
from app.core.security import hash_password, verify_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad


def ahora_utc():
    return datetime.now(timezone.utc)


async def registrar(uow, datos, settings, semaphore):
    hashed = await hash_password(datos.password, rounds=settings.bcrypt_rounds, semaphore=semaphore)
    async with uow:
        if await uow.usuarios.por_email(str(datos.email)) or await uow.usuarios.cliente_por_email(str(datos.email)):
            raise HTTPException(409, 'El correo ya está registrado')
        usuario = Usuario(nombre=datos.nombre, email=str(datos.email), password_hash=hashed)
        await uow.usuarios.add(usuario)
        await uow.usuarios.add(AsignacionRol(usuario_id=usuario.id, rol='CLIENTE'))
        await uow.usuarios.add(Cliente(nombre=datos.nombre, email=str(datos.email), usuario_id=usuario.id))
    return usuario


async def comprobar_limite(factory, email, ip, ahora):
    async with factory() as session:
        result = await session.scalars(select(IntentoAcceso).where(
            IntentoAcceso.email == email, IntentoAcceso.ip == ip,
            IntentoAcceso.cuando > ahora - timedelta(seconds=60),
        ).order_by(IntentoAcceso.cuando.desc(), IntentoAcceso.id.desc()))
        fallos = []
        for intento in result:
            if intento.exito:
                break
            fallos.append(intento)
        if len(fallos) >= 5:
            retry = max(1, ceil((fallos[4].cuando + timedelta(seconds=60) - ahora).total_seconds()))
            raise HTTPException(429, 'Demasiados intentos; vuelva a intentar', headers={'Retry-After': str(retry)})


async def guardar_intento(factory, email, ip, exito, ahora):
    # Excepción a transacción de petición: el login fallido lanza 401 y revierte
    # su UoW. Esta sesión confirma el intento para que cuente aun con rollback;
    # el costo es conservar historial de peticiones revertidas.
    async with factory() as session:
        async with session.begin():
            session.add(IntentoAcceso(email=email, ip=ip, exito=exito, cuando=ahora))


async def login(uow, datos, factory, dummy_hash, semaphore, ip):
    await comprobar_limite(factory, str(datos.email), ip, ahora_utc())
    async with uow:
        usuario = await uow.usuarios.por_email(str(datos.email))
        valid = await verify_password(datos.password, usuario.password_hash if usuario else dummy_hash, semaphore=semaphore)
        exito = bool(valid and usuario and usuario.activo)
        await guardar_intento(factory, str(datos.email), ip, exito, ahora_utc())
        if not exito:
            raise HTTPException(401, 'Credenciales inválidas')
        roles = await uow.usuarios.roles_vigentes(usuario.id, ahora_utc())
    return usuario, roles


async def cambiar_password(uow, usuario, datos, settings, semaphore):
    usuario_id, password_hash = usuario.id, usuario.password_hash
    # La dependencia leyó el usuario con autobegin; finalizar esa lectura antes
    # del trabajo costoso, y recargar dentro de la transacción de escritura.
    await uow.session.rollback()
    if not await verify_password(datos.password_actual, password_hash, semaphore=semaphore):
        raise HTTPException(401, 'Credenciales inválidas')
    hashed = await hash_password(datos.password_nueva, rounds=settings.bcrypt_rounds, semaphore=semaphore)
    async with uow:
        usuario = await uow.usuarios.por_id(usuario_id)
        if not usuario or not usuario.activo or usuario.password_hash != password_hash:
            raise HTTPException(401, 'Credenciales inválidas')
        usuario.password_hash = hashed
        usuario.debe_cambiar_password = False
        await uow.usuarios.add(usuario)
        await uow.usuarios.add(EventoSeguridad(actor=usuario.email, accion='Cambio de contraseña'))


async def exigir_admin(uow, usuario_id):
    actor = await uow.usuarios.por_id(usuario_id)
    if not actor or not actor.activo or actor.debe_cambiar_password or 'ADMIN' not in await uow.usuarios.roles_vigentes(usuario_id, ahora_utc()):
        raise HTTPException(403, 'No tiene permiso para realizar esta operación')
    return actor


async def crear_personal(uow, actor_id, datos, settings, semaphore):
    await uow.session.rollback()
    hashed = await hash_password(datos.password_provisoria, rounds=settings.bcrypt_rounds, semaphore=semaphore)
    async with uow:
        actor = await exigir_admin(uow, actor_id)
        if await uow.usuarios.por_email(str(datos.email)) or await uow.usuarios.cliente_por_email(str(datos.email)):
            raise HTTPException(409, 'El correo ya está registrado')
        user = Usuario(nombre=datos.nombre, email=str(datos.email), password_hash=hashed, debe_cambiar_password=True)
        await uow.usuarios.add(user)
        await uow.usuarios.add(AsignacionRol(usuario_id=user.id, rol=datos.rol, otorgada_por=actor.id))
        await uow.usuarios.add(EventoSeguridad(actor=actor.email, accion=f'Alta de personal {user.id}'))
    return user


async def listar_roles(uow, usuario_id):
    if not await uow.usuarios.por_id(usuario_id):
        raise HTTPException(404, 'Usuario no encontrado')
    return await uow.usuarios.historial_roles(usuario_id)


async def asignar_rol(uow, actor_id, usuario_id, datos):
    async with uow:
        actor = await exigir_admin(uow, actor_id)
        if not await uow.usuarios.por_id(usuario_id):
            raise HTTPException(404, 'Usuario no encontrado')
        ahora = ahora_utc()
        if datos.vence_en is not None and datos.vence_en <= ahora:
            raise HTTPException(422, 'El vencimiento debe ser futuro')
        anterior = await uow.usuarios.rol_abierto(usuario_id, datos.rol)
        if anterior:
            if anterior.vence_en is None or anterior.vence_en > ahora:
                raise HTTPException(409, 'El rol ya está asignado')
            anterior.revocada_en = ahora
            await uow.usuarios.add(anterior)
        nuevo = AsignacionRol(usuario_id=usuario_id, rol=datos.rol, vence_en=datos.vence_en, otorgada_por=actor.id)
        await uow.usuarios.add(nuevo)
        await uow.usuarios.add(EventoSeguridad(actor=actor.email, accion=f'Asignación de rol {datos.rol} a {usuario_id}'))
    return nuevo


async def revocar_rol(uow, actor_id, usuario_id, rol):
    async with uow:
        actor = await exigir_admin(uow, actor_id)
        if not await uow.usuarios.por_id(usuario_id):
            raise HTTPException(404, 'Usuario no encontrado')
        row = await uow.usuarios.rol_abierto(usuario_id, rol)
        if not row:
            raise HTTPException(404, 'Asignación no encontrada')
        if rol == 'ADMIN':
            if usuario_id == actor_id:
                raise HTTPException(409, 'No puede revocar su propio ADMIN')
            if not await uow.usuarios.cantidad_admin(ahora_utc(), excluir=usuario_id):
                raise HTTPException(409, 'Debe conservarse un administrador vigente')
        row.revocada_en = ahora_utc()
        await uow.usuarios.add(row)
        await uow.usuarios.add(EventoSeguridad(actor=actor.email, accion=f'Revocación de rol {rol} a {usuario_id}'))
    return {'mensaje': 'Rol revocado'}
