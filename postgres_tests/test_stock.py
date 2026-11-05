import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from postgres_tests.test_crud import api, payload
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.ventas.models import Venta


@pytest.mark.parametrize('cantidad',[1,3])
def test_alta_reposicion_venta_conservan_suma(pg_config,cantidad):
    async def run():
        async with api(pg_config) as (client,session,editorial,actor):
            book=(await client.post('/libros/',json=payload(editorial,stock=5))).json()
            customer=(await client.post('/clientes/',json=dict(nombre='C',email='stock@example.test'))).json()
            response=await client.post(f"/libros/{book['id']}/reponer",json=dict(cantidad=cantidad,motivo='Compra'))
            assert response.status_code==200,response.text
            sale=await client.post('/ventas/',json=dict(cliente_id=customer['id'],renglones=[dict(libro_id=book['id'],cantidad=cantidad+1)]))
            assert sale.status_code==201,sale.text
            stock=await session.scalar(select(Libro.stock).where(Libro.id==book['id']))
            total=await session.scalar(select(func.sum(MovimientoStock.cantidad)).where(MovimientoStock.libro_id==book['id']))
            assert stock==total==4
            moves=(await client.get(f"/libros/{book['id']}/movimientos")).json()
            assert moves['total']==3
            assert {m['usuario_id'] for m in moves['items']}=={actor}
            assert moves['items'][-1]['venta_id']==sale.json()['id']
    asyncio.run(run())


@pytest.mark.parametrize('cantidad', [1, 2])
def test_venta_varios_libros_descuenta_y_precarga_historia(pg_config, cantidad):
    async def run():
        async with api(pg_config) as (client, session, editorial, actor):
            first = (await client.post('/libros/', json=payload(editorial, isbn='multi-a', stock=5))).json()
            second = (await client.post('/libros/', json=payload(editorial, isbn='multi-b', stock=6))).json()
            customer = (await client.post('/clientes/', json=dict(nombre='C', email='multi@example.test'))).json()
            body = dict(cliente_id=customer['id'], renglones=[
                dict(libro_id=first['id'], cantidad=cantidad),
                dict(libro_id=second['id'], cantidad=cantidad + 1)])
            response = await client.post('/ventas/', json=body)
            assert response.status_code == 201, response.text
            sale = response.json()
            assert Decimal(sale['total']) == Decimal('12.50') * (2 * cantidad + 1)
            for book, sold in [(first, cantidad), (second, cantidad + 1)]:
                assert await session.scalar(select(Libro.stock).where(Libro.id == book['id'])) == book['stock'] - sold
                movement = await session.scalar(select(MovimientoStock).where(
                    MovimientoStock.libro_id == book['id'], MovimientoStock.venta_id == sale['id']))
                assert movement.cantidad == -sold and movement.usuario_id == actor
            assert (await client.delete(f"/libros/{first['id']}")).status_code == 204
            assert (await client.post('/ventas/', json=body)).status_code == 409
            assert (await client.post('/libros/', json=payload(editorial, isbn='multi-a'))).status_code == 201
            session.expunge_all()
            history = await client.get(f"/ventas/{sale['id']}")
            assert history.status_code == 200, history.text
            assert history.json() == sale
            moves = await client.get(f"/libros/{first['id']}/movimientos?size=1")
            assert moves.status_code == 200 and moves.json()['total'] == 2
            assert moves.json()['pages'] == 2
    asyncio.run(run())


@pytest.mark.parametrize('operation', ['reponer', 'venta'])
def test_fallo_movimiento_revierte_stock_y_venta(pg_config, monkeypatch, operation):
    async def run():
        from app.modules.libros.repository import MovimientoStockRepository
        async with api(pg_config) as (client, session, editorial, actor):
            book = (await client.post('/libros/', json=payload(editorial, stock=5))).json()
            customer = (await client.post('/clientes/', json=dict(nombre='C', email='rollback-stock@example.test'))).json()
            original = MovimientoStockRepository.add
            async def fail(self, movement):
                await original(self, movement)
                raise RuntimeError('fallo despues de guardar movimiento')
            monkeypatch.setattr(MovimientoStockRepository, 'add', fail)
            with pytest.raises(RuntimeError):
                if operation == 'reponer':
                    await client.post(f"/libros/{book['id']}/reponer", json=dict(cantidad=2, motivo='Compra'))
                else:
                    await client.post('/ventas/', json=dict(cliente_id=customer['id'],
                        renglones=[dict(libro_id=book['id'], cantidad=2)]))
            assert await session.scalar(select(Libro.stock).where(Libro.id == book['id'])) == 5
            assert await session.scalar(select(func.count()).select_from(MovimientoStock)) == 1
            assert await session.scalar(select(func.count()).select_from(Venta)) == 0
    asyncio.run(run())


@pytest.mark.parametrize('role', [None, 'VENDEDOR'])
def test_inventario_solo_admin_real(pg_config, role):
    async def run():
        from app.main import app as configured
        from app.modules.usuarios.models import AsignacionRol
        from postgres_tests.test_auth import api as authenticated_api, account
        async with authenticated_api(pg_config) as (client, factory, app):
            app.router.routes = list(configured.router.routes)
            data = account()
            uid = (await client.post('/auth/registro', json=data)).json()['id']
            if role:
                async with factory.begin() as session:
                    session.add(AsignacionRol(usuario_id=uid, rol=role))
            await client.post('/auth/login', json={key: data[key] for key in ('email', 'password')})
            assert (await client.get('/libros/1/movimientos')).status_code == 403
            assert (await client.post('/libros/1/reponer', json=dict(cantidad=1, motivo='Compra'))).status_code == 403
    asyncio.run(run())


@pytest.mark.parametrize('invalid',['stock','libro'])
def test_venta_fallida_revierte_todos_los_renglones(pg_config,invalid):
    async def run():
        async with api(pg_config) as (client,session,editorial,actor):
            first=(await client.post('/libros/',json=payload(editorial,isbn='a',stock=5))).json()
            second=(await client.post('/libros/',json=payload(editorial,isbn='b',stock=0))).json()
            customer=(await client.post('/clientes/',json=dict(nombre='C',email='failure@example.test'))).json()
            second_id=second['id'] if invalid=='stock' else 2147483647
            response=await client.post('/ventas/',json=dict(cliente_id=customer['id'],renglones=[dict(libro_id=first['id'],cantidad=2),dict(libro_id=second_id,cantidad=1)]))
            assert response.status_code==409,response.text
            assert await session.scalar(select(func.count()).select_from(Venta))==0
            assert await session.scalar(select(Libro.stock).where(Libro.id==first['id']))==5
            assert await session.scalar(select(func.count()).select_from(MovimientoStock))==1
    asyncio.run(run())


@pytest.mark.parametrize('bad',[0,-2])
def test_reposicion_invalida_y_baja_no_escriben(pg_config,bad):
    async def run():
        async with api(pg_config) as (client,session,editorial,actor):
            book=(await client.post('/libros/',json=payload(editorial))).json()
            path=f"/libros/{book['id']}/reponer"
            assert (await client.post(path,json=dict(cantidad=bad,motivo='Compra'))).status_code==422
            assert (await client.delete(f"/libros/{book['id']}")).status_code==204
            assert (await client.post(path,json=dict(cantidad=2,motivo='Compra'))).status_code==409
            replacement=await client.post('/libros/',json=payload(editorial))
            assert replacement.status_code==201,replacement.text
            assert (await client.post('/libros/',json=payload(editorial))).status_code==409
    asyncio.run(run())
