import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pathlib import Path

import bcrypt
import httpx
import jwt
import pytest
from fastapi import FastAPI, APIRouter, Depends
from sqlalchemy import select, func, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import Settings
from app.modules.usuarios.models import Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
from app.modules.clientes.models import Cliente
from app.modules.ventas.models import Venta
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.autores.models import Autor
from app.modules.usuarios.router import router
from app.modules.libros.router import public_router as libros_publico, protected_router as libros_protegido
from app.core.dependencies import verificar_cambio_obligatorio


@asynccontextmanager
async def api(config):
    url=URL.create('postgresql+asyncpg',username=config['user'],password=config['password'],
                   host=config['host'],port=config['port'],database=config['database'])
    engine=create_async_engine(url)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    app=FastAPI(); app.include_router(router); app.include_router(libros_publico)
    protegido=APIRouter(dependencies=[Depends(verificar_cambio_obligatorio)])
    protegido.include_router(libros_protegido); app.include_router(protegido)
    app.state.session_factory=factory
    app.state.settings=Settings(_env_file=None,postgres_user='test',postgres_password='test',postgres_host='localhost',
        postgres_db='test',jwt_secret='test-signature-longer-than-32-bytes-for-auth',bcrypt_rounds=4)
    app.state.bcrypt_semaphore=asyncio.Semaphore(1)
    app.state.dummy_password_hash=bcrypt.hashpw(b'dummy-password',bcrypt.gensalt(rounds=4)).decode()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            yield client,factory,app
    finally:
        # Sólo el cluster temporal validado por pg_config. Los intentos usan
        # commits reales: no quedan aislados por un rollback de sesión fixture.
        async with engine.begin() as connection:
            assert Path(await connection.scalar(text('SHOW data_directory'))).resolve()==Path(config['data_directory']).resolve()
            assert await connection.scalar(select(func.current_database()))==config['database']
            await connection.execute(text('TRUNCATE usuario, cliente, libro, editorial, autor, genero, intento_acceso, evento_seguridad RESTART IDENTITY CASCADE'))
        await engine.dispose()


def account():
    return dict(nombre='Ana',email=f'{uuid4().hex}@example.com',password='abcdefgh')


@pytest.mark.parametrize('conflict',['usuario','cliente'])
def test_registro_atomico_y_conflictos(pg_config,conflict):
    async def scenario():
        async with api(pg_config) as (client,factory,app):
            data=account()
            if conflict=='cliente':
                async with factory.begin() as session: session.add(Cliente(nombre='Anterior',email=data['email']))
                response=await client.post('/auth/registro',json=data)
                assert response.status_code==409
            else:
                response=await client.post('/auth/registro',json=data)
                assert response.status_code==201 and 'password_hash' not in response.text
                assert (await client.post('/auth/registro',json=data)).status_code==409
            async with factory() as session:
                user=await session.scalar(select(Usuario).where(Usuario.email==data['email']))
                assert (user is None)==(conflict=='cliente')
                if user:
                    assert bcrypt.checkpw(data['password'].encode(),user.password_hash.encode())
                    assert await session.scalar(select(func.count()).select_from(AsignacionRol).where(AsignacionRol.usuario_id==user.id,AsignacionRol.rol=='CLIENTE'))==1
                    assert await session.scalar(select(func.count()).select_from(Cliente).where(Cliente.usuario_id==user.id))==1
    asyncio.run(scenario())


@pytest.mark.parametrize('exists',[False,True])
def test_login_no_enumeracion_limite_y_persistencia(pg_config,exists,monkeypatch):
    async def scenario():
        async with api(pg_config) as (client,factory,app):
            data=account()
            if exists: assert (await client.post('/auth/registro',json=data)).status_code==201
            calls=[]; original=bcrypt.checkpw
            def check(password,hashed): calls.append(hashed); return original(password,hashed)
            monkeypatch.setattr(bcrypt,'checkpw',check)
            login=dict(email=data['email'],password='incorrecta')
            for _ in range(5):
                response=await client.post('/auth/login',json=login)
                assert response.status_code==401 and response.json()=={'detail':'Credenciales inválidas'}
            response=await client.post('/auth/login',json=login)
            assert response.status_code==429 and 1<=int(response.headers['retry-after'])<=60
            assert len(calls)==5
            async with factory() as session:
                assert await session.scalar(select(func.count()).select_from(IntentoAcceso).where(IntentoAcceso.email==data['email']))==5
    asyncio.run(scenario())


@pytest.mark.parametrize('secure',[False,True])
def test_cookie_sesion_cambio_y_logout(pg_config,secure):
    async def scenario():
        async with api(pg_config) as (client,factory,app):
            app.state.settings.cookie_secure=secure
            if secure: client.base_url='https://test'
            data=account(); assert (await client.post('/auth/registro',json=data)).status_code==201
            login={k:data[k] for k in ('email','password')}
            for _ in range(2): assert (await client.post('/auth/login',json={**login,'password':'incorrecta'})).status_code==401
            response=await client.post('/auth/login',json=login)
            assert response.status_code==200 and 'token' not in response.text
            cookie=response.headers['set-cookie']; token=client.cookies.get('access_token')
            assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Max-Age=1800' in cookie
            assert ('Secure' in cookie)==secure
            yo=await client.get('/auth/yo'); assert yo.status_code==200 and 'password_hash' not in yo.text
            assert yo.json()['roles_vigentes']==['CLIENTE'] and yo.json()['roles_token']==['CLIENTE']
            uid=yo.json()['usuario']['id']
            async with factory.begin() as session:
                user=await session.get(Usuario,uid); user.debe_cambiar_password=True
            response=await client.post('/auth/cambiar-password',json=dict(password_actual='incorrecta',password_nueva='nueva-clave'))
            assert response.status_code==401
            response=await client.post('/auth/cambiar-password',json=dict(password_actual=data['password'],password_nueva='nueva-clave'))
            assert response.status_code==200 and 'set-cookie' not in response.headers
            assert client.cookies.get('access_token')==token
            assert (await client.get('/auth/yo')).json()['usuario']['debe_cambiar_password'] is False
            async with factory() as session:
                assert await session.scalar(select(func.count()).select_from(EventoSeguridad).where(EventoSeguridad.actor==data['email']))==1
            assert (await client.post('/auth/login',json={**login,'password':'incorrecta'})).status_code==401
            async with factory() as session:
                assert await session.scalar(select(func.count()).select_from(IntentoAcceso).where(IntentoAcceso.email==data['email']))==4
            assert (await client.post('/auth/logout')).status_code==200
            assert (await client.get('/auth/yo')).status_code==401
            assert (await client.post('/auth/logout')).status_code==200
    asyncio.run(scenario())


@pytest.mark.parametrize('kind',['bearer','expired','missing','inactive','badsub'])
def test_sesion_rechazada(pg_config,kind):
    async def scenario():
        async with api(pg_config) as (client,factory,app):
            data=account(); await client.post('/auth/registro',json=data)
            await client.post('/auth/login',json={k:data[k] for k in ('email','password')})
            token=client.cookies.get('access_token'); claims=jwt.decode(token,app.state.settings.jwt_secret.get_secret_value(),algorithms=['HS256'])
            client.cookies.clear()
            headers={}
            if kind=='bearer': headers['Authorization']='Bearer '+token
            elif kind=='expired':
                claims['exp']=datetime.now(timezone.utc)-timedelta(seconds=1)
                client.cookies.set('access_token',jwt.encode(claims,app.state.settings.jwt_secret.get_secret_value(),algorithm='HS256'))
            elif kind=='badsub':
                claims['sub']='99999999999999999999999999999999'
                client.cookies.set('access_token',jwt.encode(claims,app.state.settings.jwt_secret.get_secret_value(),algorithm='HS256'))
            elif kind in ('missing','inactive'):
                async with factory.begin() as session:
                    user=await session.get(Usuario,int(claims['sub']))
                    if kind=='inactive': user.activo=False
                    else: claims['sub']='2147483647'
                client.cookies.set('access_token',jwt.encode(claims,app.state.settings.jwt_secret.get_secret_value(),algorithm='HS256'))
            assert (await client.get('/auth/yo',headers=headers)).status_code==401
    asyncio.run(scenario())


@pytest.mark.parametrize('state',['revocado','vencido','cambio'])
def test_alta_solo_admin_vigente_db(pg_config,state):
    async def scenario():
        async with api(pg_config) as (client,factory,app):
            data=account(); await client.post('/auth/registro',json=data)
            async with factory.begin() as session:
                user=await session.scalar(select(Usuario).where(Usuario.email==data['email']))
                user_id=user.id
                role=AsignacionRol(usuario_id=user.id,rol='ADMIN')
                session.add(role)
                editorial=Editorial(nombre=uuid4().hex,pais='AR'); session.add(editorial)
                await session.flush(); editorial_id=editorial.id; role_id=role.id
            await client.post('/auth/login',json={k:data[k] for k in ('email','password')})
            payload=dict(isbn=uuid4().hex[:20],titulo='L',precio='2.00',stock_inicial=2,editorial_id=editorial_id)
            assert (await client.post('/libros/',json=payload)).status_code==201
            async with factory.begin() as session:
                role=await session.get(AsignacionRol,role_id)
                if state=='revocado': role.revocada_en=datetime.now(timezone.utc)
                elif state=='vencido': role.vence_en=datetime.now(timezone.utc)-timedelta(seconds=1)
                else: (await session.get(Usuario,user_id)).debe_cambiar_password=True
            yo=(await client.get('/auth/yo')).json()
            assert 'ADMIN' in yo['roles_token']
            if state!='cambio': assert 'ADMIN' not in yo['roles_vigentes']
            assert (await client.post('/libros/',json={**payload,'isbn':uuid4().hex[:20]})).status_code==403
    asyncio.run(scenario())


@pytest.mark.parametrize('at_boundary',[True,False])
def test_ventana_ip_y_reinicio_con_historial(pg_config,at_boundary):
    async def scenario():
        from app.modules.usuarios import service
        async with api(pg_config) as (client,factory,app):
            data=account(); await client.post('/auth/registro',json=data)
            now=datetime.now(timezone.utc)
            async with factory.begin() as session:
                for i in range(5): session.add(IntentoAcceso(email=data['email'],ip='127.0.0.1',exito=False,
                    cuando=now-timedelta(seconds=60 if at_boundary else 61)))
                for i in range(5): session.add(IntentoAcceso(email=data['email'],ip='otra-ip',exito=False,cuando=now))
            await service.comprobar_limite(factory,data['email'],'127.0.0.1',now)
            assert (await client.post('/auth/login',json={k:data[k] for k in ('email','password')})).status_code==200
            for i in range(4): assert (await client.post('/auth/login',json=dict(email=data['email'],password='incorrecta'))).status_code==401
            assert (await client.post('/auth/login',json={k:data[k] for k in ('email','password')})).status_code==200
            assert (await client.post('/auth/login',json=dict(email=data['email'],password='incorrecta'))).status_code==401
    asyncio.run(scenario())


@pytest.mark.parametrize('operation',['registro','cambio'])
def test_rollback_inyeccion_error_atomicidad(pg_config,operation,monkeypatch):
    async def scenario():
        from app.modules.usuarios.repository import UsuarioRepository
        async with api(pg_config) as (client,factory,app):
            data=account()
            if operation=='cambio':
                await client.post('/auth/registro',json=data)
                await client.post('/auth/login',json={k:data[k] for k in ('email','password')})
            original=UsuarioRepository.add
            async def fail(self,entity):
                await original(self,entity)
                if isinstance(entity,Cliente if operation=='registro' else EventoSeguridad):
                    raise RuntimeError('fallo simulado después de flush')
            monkeypatch.setattr(UsuarioRepository,'add',fail)
            with pytest.raises(RuntimeError):
                if operation=='registro': await client.post('/auth/registro',json=data)
                else: await client.post('/auth/cambiar-password',json=dict(password_actual=data['password'],password_nueva='nueva-clave'))
            async with factory() as session:
                user=await session.scalar(select(Usuario).where(Usuario.email==data['email']))
                if operation=='registro':
                    assert user is None
                    assert await session.scalar(select(func.count()).select_from(Cliente).where(Cliente.email==data['email']))==0
                else:
                    assert bcrypt.checkpw(data['password'].encode(),user.password_hash.encode())
                    assert await session.scalar(select(func.count()).select_from(EventoSeguridad).where(EventoSeguridad.actor==data['email']))==0
    asyncio.run(scenario())
