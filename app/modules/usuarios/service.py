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
