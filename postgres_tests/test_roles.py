import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, func

from postgres_tests.test_auth import api, account
from app.modules.usuarios.models import Usuario, AsignacionRol, EventoSeguridad
from app.modules.usuarios.router import admin_router
from app.modules.clientes.models import Cliente
from app.modules.ventas.models import Venta
from decimal import Decimal


async def admin(client, factory, *, email=None):
    data = account()
    if email:
        data['email'] = email
    assert (await client.post('/auth/registro', json=data)).status_code == 201
    async with factory.begin() as session:
        user = await session.scalar(select(Usuario).where(Usuario.email == data['email']))
        session.add(AsignacionRol(usuario_id=user.id, rol='ADMIN'))
        uid = user.id
    await client.post('/auth/login', json={k:data[k] for k in ('email','password')})
    return data, uid


@pytest.mark.parametrize('rol', ['ADMIN', 'VENDEDOR'])
def test_personal_provisional_y_evento_atomico(pg_config, rol):
    async def scenario():
        async with api(pg_config) as (client, factory, app):
            app.include_router(admin_router)
            _, actor = await admin(client, factory)
            body = dict(nombre='Personal', email='personal@example.com', password_provisoria='abcdefgh', rol=rol)
            response = await client.post('/usuarios', json=body)
            assert response.status_code == 201, response.text
            user = response.json()
            assert user['debe_cambiar_password'] is True and 'password_hash' not in response.text
            assert (await client.post('/usuarios', json=body)).status_code == 409
            async with factory() as session:
                role = await session.scalar(select(AsignacionRol).where(AsignacionRol.usuario_id == user['id']))
                assert role.rol == rol and role.otorgada_por == actor
                assert await session.scalar(select(func.count()).select_from(EventoSeguridad)) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize('expired', [False, True])
def test_roles_historia_reasignacion_revocacion(pg_config, expired):
    async def scenario():
        async with api(pg_config) as (client, factory, app):
            app.include_router(admin_router)
            await admin(client, factory)
            response = await client.post('/auth/registro', json=account())
            uid = response.json()['id']
            path = f'/usuarios/{uid}/roles'
            assert (await client.post(path, json={'rol':'VENDEDOR'})).status_code == 201
            assert (await client.post(path, json={'rol':'VENDEDOR'})).status_code == 409
            if expired:
                async with factory.begin() as session:
                    role = await session.scalar(select(AsignacionRol).where(AsignacionRol.usuario_id==uid, AsignacionRol.rol=='VENDEDOR'))
                    role.vence_en = datetime.now(timezone.utc)-timedelta(days=1)
                assert (await client.post(path, json={'rol':'VENDEDOR'})).status_code == 201
            assert (await client.delete(path+'/VENDEDOR')).status_code == 200
            roles = (await client.get(path)).json()
            rows = [r for r in roles if r['rol']=='VENDEDOR']
            assert len(rows) == (2 if expired else 1)
            assert all(r['revocada_en'] is not None for r in rows)
            assert (await client.delete(path+'/VENDEDOR')).status_code == 404
    asyncio.run(scenario())


@pytest.mark.parametrize('kind', ['self', 'other'])
def test_admin_autorrevocacion_y_continuidad(pg_config, kind):
    async def scenario():
        async with api(pg_config) as (client, factory, app):
            app.include_router(admin_router)
            _, uid = await admin(client, factory)
            assert (await client.delete(f'/usuarios/{uid}/roles/ADMIN')).status_code == 409
            if kind == 'other':
                target = (await client.post('/auth/registro', json=account())).json()['id']
                assert (await client.post(f'/usuarios/{target}/roles', json={'rol':'ADMIN'})).status_code == 201
                assert (await client.delete(f'/usuarios/{target}/roles/ADMIN')).status_code == 200
                assert (await client.get(f'/usuarios/{uid}/roles')).status_code == 200
    asyncio.run(scenario())


@pytest.mark.parametrize('operation', ['personal', 'rol'])
def test_rollback_cambio_si_falla_evento(pg_config, monkeypatch, operation):
    async def scenario():
        from app.modules.usuarios.repository import UsuarioRepository
        async with api(pg_config) as (client, factory, app):
            app.include_router(admin_router)
            await admin(client, factory)
            target = (await client.post('/auth/registro', json=account())).json()['id']
            original = UsuarioRepository.add
            async def fail(self, entity):
                await original(self, entity)
                if isinstance(entity, EventoSeguridad):
                    raise RuntimeError('evento fallido')
            monkeypatch.setattr(UsuarioRepository, 'add', fail)
            with pytest.raises(RuntimeError):
                if operation == 'personal':
                    await client.post('/usuarios', json=dict(nombre='P', email='rollback@example.com', password_provisoria='abcdefgh', rol='VENDEDOR'))
                else:
                    await client.post(f'/usuarios/{target}/roles', json={'rol':'VENDEDOR'})
            async with factory() as session:
                assert await session.scalar(select(func.count()).select_from(EventoSeguridad)) == 0
                assert await session.scalar(select(Usuario).where(Usuario.email=='rollback@example.com')) is None
                assert await session.scalar(select(AsignacionRol).where(AsignacionRol.usuario_id==target, AsignacionRol.rol=='VENDEDOR')) is None
    asyncio.run(scenario())


@pytest.mark.parametrize('role', [None, 'VENDEDOR'])
def test_propiedad_detalle_y_mis_ventas(pg_config, role):
    async def scenario():
        from app.main import app as configured
        async with api(pg_config) as (client, factory, app):
            app.router.routes = list(configured.router.routes)
            data = account()
            owner = (await client.post('/auth/registro', json=data)).json()['id']
            other = (await client.post('/auth/registro', json=account())).json()['id']
            async with factory.begin() as session:
                first = await session.scalar(select(Cliente).where(Cliente.usuario_id==owner))
                second = await session.scalar(select(Cliente).where(Cliente.usuario_id==other))
                own = Venta(cliente_id=first.id, total=Decimal('0'))
                foreign = Venta(cliente_id=second.id, total=Decimal('0'))
                session.add_all([own, foreign])
                if role:
                    session.add(AsignacionRol(usuario_id=owner, rol=role))
                await session.flush()
                ownid, otherid = own.id, foreign.id
                # Lo propio no requiere conservar ni siquiera el rol CLIENTE.
                if role is None:
                    row = await session.scalar(select(AsignacionRol).where(AsignacionRol.usuario_id==owner))
                    row.revocada_en = datetime.now(timezone.utc)
            await client.post('/auth/login', json={k:data[k] for k in ('email','password')})
            assert (await client.get(f'/ventas/{ownid}')).status_code == 200
            assert (await client.get(f'/ventas/{otherid}')).status_code == (200 if role else 403)
            response = await client.get('/mis-ventas')
            assert response.status_code == 200
            assert response.json()['total'] == 1
            assert [r['id'] for r in response.json()['items']] == [ownid]
            assert (await client.get('/mis-ventas?page=2')).status_code == 422
            assert (await client.get('/ventas/2147483647')).status_code == 404
    asyncio.run(scenario())


@pytest.mark.parametrize('role', ['ADMIN', 'VENDEDOR'])
def test_grupo_protegido_cambio_y_revocacion_cookie(pg_config, role):
    async def scenario():
        from app.main import app as configured
        async with api(pg_config) as (client, factory, app):
            app.router.routes = list(configured.router.routes)
            data = account()
            uid = (await client.post('/auth/registro', json=data)).json()['id']
            async with factory.begin() as session:
                session.add(AsignacionRol(usuario_id=uid, rol=role))
                user = await session.get(Usuario, uid)
                user.debe_cambiar_password = True
            await client.post('/auth/login', json={k:data[k] for k in ('email','password')})
            token = client.cookies.get('access_token')
            assert (await client.get('/ventas/')).status_code == 403
            assert (await client.get('/mis-ventas')).status_code == 403
            assert (await client.get('/auth/yo')).status_code == 200
            assert (await client.get('/libros/')).status_code == 200
            assert (await client.post('/auth/cambiar-password', json=dict(password_actual=data['password'],password_nueva='nueva-clave'))).status_code == 200
            assert client.cookies.get('access_token') == token
            assert (await client.get('/ventas/')).status_code == 200
            assert (await client.post('/generos/',json={'nombre':'Unico'})).status_code == (201 if role=='ADMIN' else 403)
            async with factory.begin() as session:
                row=await session.scalar(select(AsignacionRol).where(AsignacionRol.usuario_id==uid, AsignacionRol.rol==role))
                row.revocada_en=datetime.now(timezone.utc)
            assert (await client.get('/ventas/')).status_code == 403
            assert (await client.get('/mis-ventas')).status_code == 200
    asyncio.run(scenario())


@pytest.mark.parametrize('role', ['ADMIN', 'VENDEDOR'])
def test_eventos_paginados_solo_admin(pg_config, role):
    async def scenario():
        from app.main import app as configured
        async with api(pg_config) as (client, factory, app):
            app.router.routes = list(configured.router.routes)
            data=account()
            uid=(await client.post('/auth/registro',json=data)).json()['id']
            async with factory.begin() as session:
                session.add(AsignacionRol(usuario_id=uid,rol=role))
                session.add_all([EventoSeguridad(actor='SISTEMA',accion='uno'), EventoSeguridad(actor='SISTEMA',accion='dos')])
            await client.post('/auth/login',json={k:data[k] for k in ('email','password')})
            response=await client.get('/eventos?size=1&page=2')
            assert response.status_code == (200 if role=='ADMIN' else 403)
            if role=='ADMIN':
                assert response.json()['total']==2 and response.json()['pages']==2
                assert response.json()['items'][0]['accion']=='dos'
                assert (await client.get('/eventos?size=1&page=3')).status_code==422
                assert (await client.get('/eventos?size=101')).status_code==422
    asyncio.run(scenario())


@pytest.mark.parametrize('failure', [False, True])
def test_seed_evento_real_y_rollback(pg_config, monkeypatch, failure):
    async def scenario():
        import seed
        from app.modules.editoriales.models import Editorial
        async with api(pg_config) as (client,factory,app):
            original=seed.agregar
            if failure:
                async def fail(session,*entities):
                    await original(session,*entities)
                    if any(isinstance(e,EventoSeguridad) for e in entities):
                        raise RuntimeError('evento fallido')
                monkeypatch.setattr(seed,'agregar',fail)
            async with factory() as session:
                if failure:
                    with pytest.raises(RuntimeError):
                        await seed.cargar(session)
                    await session.rollback()
                else:
                    await seed.cargar(session)
            async with factory() as session:
                assert await session.scalar(select(func.count()).select_from(EventoSeguridad).where(
                    EventoSeguridad.actor=='SISTEMA', EventoSeguridad.accion=='Carga de los datos iniciales')) == (0 if failure else 1)
                assert await session.scalar(select(func.count()).select_from(Editorial)) == (0 if failure else 3)
    asyncio.run(scenario())
