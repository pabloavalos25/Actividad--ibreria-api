import asyncio
import logging

import pytest

from app.modules.ventas import router


@pytest.mark.parametrize('sale_id,email,total', [(17, 'ana@example.test', '12.50'), (28, 'tom@example.test', '25.00')])
def test_comprobante_espera_medio_segundo_sin_bloquear_y_emite_una_vez(monkeypatch, caplog, sale_id, email, total):
    async def run():
        original_sleep = asyncio.sleep
        waiting, release = asyncio.Event(), asyncio.Event()
        delays, progress = [], []

        async def controlled_sleep(delay):
            delays.append(delay)
            waiting.set()
            await release.wait()

        monkeypatch.setattr(router.asyncio, 'sleep', controlled_sleep)
        with caplog.at_level(logging.INFO, logger='libreria.ventas'):
            task = asyncio.create_task(router.enviar_comprobante(sale_id, email, total))
            await asyncio.wait_for(waiting.wait(), 2)
            # Una tarea distinta debe avanzar mientras el comprobante espera.
            async def other_work():
                await original_sleep(0)
                progress.append('otra tarea termino')
            await asyncio.wait_for(asyncio.create_task(other_work()), 2)
            assert progress == ['otra tarea termino'] and not task.done()
            assert not [r for r in caplog.records if r.name == 'libreria.ventas']
            release.set()
            await task
        assert delays == [0.5]
        messages = [r.getMessage() for r in caplog.records if r.name == 'libreria.ventas']
        assert messages == [f'Comprobante de venta #{sale_id} enviado a {email} (total {total})']

    asyncio.run(run())
