"""Orden ASGI real y UoW PostgreSQL; no medir la duración de HTTPX."""

import asyncio

import pytest
from sqlalchemy import func, select
from starlette.background import BackgroundTasks

from app.modules.libros.repository import MovimientoStockRepository
from app.modules.ventas import router as sales_router
from app.modules.ventas.models import Venta
from postgres_tests.test_crud import api, payload


@pytest.mark.parametrize('outcome,quantity', [
    ('success', 1), ('success', 2), ('conflict', 4), ('write', 1), ('commit', 1),
])
def test_comprobante_despues_de_commit_y_cuerpo_solo_si_confirma(pg_config, monkeypatch, outcome, quantity):
    async def run():
        async with api(pg_config) as (client, session, editorial, actor):
            book = (await client.post('/libros/', json=payload(editorial, stock=3))).json()
            customer = (await client.post('/clientes/', json=dict(nombre='C', email='receipt@example.test'))).json()
            events, receipts = [], []
            original_commit = session.commit
            original_add = BackgroundTasks.add_task
            application = client._transport.app

            async def commit():
                if outcome == 'commit':
                    raise RuntimeError('fallo de commit simulado')
                await original_commit()
                events.append('commit')

            def schedule(self, function, *args, **kwargs):
                events.append('schedule')
                return original_add(self, function, *args, **kwargs)

            async def receipt(venta_id, cliente_email, total):
                events.append('receipt')
                receipts.append((venta_id, cliente_email, total))

            async def observe(scope, receive, send):
                async def tracked_send(message):
                    await send(message)
                    if message['type'] == 'http.response.body' and not message.get('more_body', False):
                        events.append('body')
                await application(scope, receive, tracked_send)

            monkeypatch.setattr(session, 'commit', commit)
            monkeypatch.setattr(BackgroundTasks, 'add_task', schedule)
            monkeypatch.setattr(sales_router, 'enviar_comprobante', receipt)
            client._transport.app = observe
            if outcome == 'write':
                original_movement = MovimientoStockRepository.add

                async def fail(self, movement):
                    await original_movement(self, movement)
                    raise RuntimeError('fallo despues de flush')

                monkeypatch.setattr(MovimientoStockRepository, 'add', fail)

            body = dict(cliente_id=customer['id'], renglones=[dict(libro_id=book['id'], cantidad=quantity)])
            if outcome in ('write', 'commit'):
                with pytest.raises(RuntimeError):
                    await client.post('/ventas/', json=body)
            else:
                response = await client.post('/ventas/', json=body)
                assert response.status_code == (201 if outcome == 'success' else 409), response.text

            if outcome == 'success':
                assert events == ['commit', 'schedule', 'body', 'receipt']
                sale = response.json()
                assert receipts == [(sale['id'], customer['email'], sale['total'])]
                assert await session.scalar(select(func.count()).select_from(Venta)) == 1
            else:
                assert 'schedule' not in events and 'receipt' not in events
                assert receipts == []
                assert await session.scalar(select(func.count()).select_from(Venta)) == 0

    asyncio.run(run())
