import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
from importlib import import_module

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, func
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.core.database import get_session
from app.core.dependencies import requerir_usuario_id
from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from app.modules.usuarios.models import Usuario
from app.modules.ventas.models import Venta
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, MovimientoStock


@asynccontextmanager
async def api(config):
    url=URL.create('postgresql+asyncpg',username=config['user'],password=config['password'],
                   host=config['host'],port=config['port'],database=config['database'])
    engine=create_async_engine(url)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(select(func.current_database())) == config['database']
            transaction=await connection.begin_nested() if connection.in_transaction() else await connection.begin()
            async with AsyncSession(bind=connection,expire_on_commit=False,join_transaction_mode='create_savepoint') as session:
                user=Usuario(email='actor-ej3@example.test',nombre='Actor',password_hash='hash')
                editorial=Editorial(nombre='Editorial ej3',pais='AR')
                session.add_all([user,editorial]); await session.commit()
                user_id = user.id
                app=FastAPI()
                for name in ['libros','ventas','autores','editoriales','generos','clientes']:
                    app.include_router(import_module(f'app.modules.{name}.router').router)
                app.dependency_overrides[get_session]=lambda:session
                app.dependency_overrides[requerir_usuario_id]=lambda:user_id
                async def actor_actual():
                    return await session.get(Usuario, user_id)
                app.dependency_overrides[requiere_admin]=actor_actual
                app.dependency_overrides[requiere_personal]=actor_actual
                app.dependency_overrides[get_usuario_actual]=actor_actual
                from app.modules.usuarios.models import AsignacionRol
                session.add(AsignacionRol(usuario_id=user.id, rol='ADMIN'))
                await session.commit()
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                    yield client,session,editorial.id,user_id
            await transaction.rollback()
    finally:
        await engine.dispose()


def payload(editorial,*,isbn='ej3',stock=3,titulo='Novela'):
    return dict(isbn=isbn,titulo=titulo,precio='12.50',stock_inicial=stock,editorial_id=editorial)


@pytest.mark.parametrize('stock',[0,3])
def test_alta_http_real_movimiento_y_rollback_conflicto(pg_config,stock):
    async def scenario():
        async with api(pg_config) as (client,session,editorial,user):
            data=payload(editorial,stock=stock)
            created=await client.post('/libros/',json=data)
            assert created.status_code == 201,created.text
            book=created.json()
            assert book['stock'] == stock
            movimientos=(await session.execute(select(MovimientoStock).where(MovimientoStock.libro_id==book['id']))).scalars().all()
            assert [m.cantidad for m in movimientos] == ([stock] if stock else [])
            if stock:
                assert movimientos[0].usuario_id == user
                assert movimientos[0].motivo == 'Stock inicial'
            failed=await client.post('/libros/',json=data)
            assert failed.status_code == 409
            assert 'INSERT' not in failed.text and 'asyncpg' not in failed.text
            assert await session.scalar(select(func.count()).select_from(Libro)) == 1
            assert await session.scalar(select(func.count()).select_from(MovimientoStock)) == (1 if stock else 0)
    asyncio.run(scenario())


@pytest.mark.parametrize('search,expected',[('nOvElA',2),("' OR 1=1 --",0)])
def test_busqueda_total_pagina_y_baja_real(pg_config,search,expected):
    async def scenario():
        async with api(pg_config) as (client,session,editorial,user):
            first=await client.post('/libros/',json=payload(editorial,isbn='a'))
            await client.post('/libros/',json=payload(editorial,isbn='b',titulo='NOVELA dos'))
            await client.post('/libros/',json=payload(editorial,isbn='c',titulo='Otro'))
            response=await client.get('/libros/',params=dict(titulo=search,size=1))
            assert response.status_code == 200,response.text
            page=response.json()
            assert page['total'] == expected and page['pages'] == max(1,expected)
            assert len(page['items']) == min(1,expected)
            assert (await client.get('/libros/',params=dict(titulo=search,size=1,page=max(1,expected)+1))).status_code == 422
            book_id=first.json()['id']
            assert (await client.delete(f'/libros/{book_id}')).status_code == 204
            assert (await client.get(f'/libros/{book_id}')).status_code == 404
            assert (await client.delete(f'/libros/{book_id}')).status_code == 404
            catalog=(await client.get('/libros/')).json()
            assert catalog['total'] == 2
            assert book_id not in [x['id'] for x in catalog['items']]
    asyncio.run(scenario())


@pytest.mark.parametrize('cantidad',[1,3])
def test_venta_decimal_dto_y_libro_baja(pg_config,cantidad):
    async def scenario():
        async with api(pg_config) as (client,session,editorial,user):
            author=(await client.post('/autores/',json=dict(nombre='Autor',nacionalidad='AR'))).json()
            genre=(await client.post('/generos/',json=dict(nombre='Género'))).json()
            data=payload(editorial)
            data.update(genero_id=genre['id'], autores=[dict(autor_id=author['id'],rol='autor',orden=1)])
            book=(await client.post('/libros/',json=data)).json()
            customer=(await client.post('/clientes/',json=dict(nombre='Cliente',email='ej3@example.test'))).json()
            body=dict(cliente_id=customer['id'],renglones=[dict(libro_id=book['id'],cantidad=cantidad)])
            response=await client.post('/ventas/',json=body)
            assert response.status_code == 201,response.text
            sale=response.json()
            assert Decimal(sale['total']) == Decimal('12.50')*cantidad
            assert Decimal(sale['renglones'][0]['precio_unitario']) == Decimal('12.50')
            assert Decimal(sale['renglones'][0]['subtotal']) == Decimal(sale['total'])
            assert (await client.patch(f"/ventas/{sale['id']}",json={})).status_code == 405
            assert (await client.patch(f"/libros/{book['id']}",json=dict(titulo='Nuevo'))).json()['precio'] == '12.50'
            assert (await client.delete(f"/libros/{book['id']}")).status_code == 204
            for route in [f"/autores/{author['id']}/libros",f"/generos/{genre['id']}/libros",f'/editoriales/{editorial}/libros']:
                page=(await client.get(route)).json()
                assert page['items'] == [] and page['total'] == 0 and page['pages'] == 1
            assert (await client.get(f"/ventas/{sale['id']}")).json()['renglones'][0]['titulo'] == 'Nuevo'
            assert (await client.post('/ventas/',json=body)).status_code == 409
            assert (await client.get('/ventas/')).json()['total'] == 1
    asyncio.run(scenario())


@pytest.mark.parametrize('actor',[-1,2147483647])
def test_actor_inexistente_revierte_alta_y_movimiento(pg_config,actor):
    async def scenario():
        async with api(pg_config) as (client,session,editorial,user):
            client._transport.app.dependency_overrides[requerir_usuario_id]=lambda:actor
            response=await client.post('/libros/',json=payload(editorial))
            assert response.status_code == 409
            assert await session.scalar(select(func.count()).select_from(Libro)) == 0
            assert await session.scalar(select(func.count()).select_from(MovimientoStock)) == 0
    asyncio.run(scenario())
