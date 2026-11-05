import asyncio

import pytest

from app.core.database import create_engine_and_factory


@pytest.mark.parametrize('size,overflow', [(2, 0), (7, 3)])
def test_pool_respeta_configuracion_sin_abrir_conexiones(size, overflow):
    async def scenario():
        engine, factory = create_engine_and_factory(
            'postgresql+asyncpg://test:test@127.0.0.1:1/test',
            pool_size=size, max_overflow=overflow,
        )
        try:
            assert engine.pool.size() == size
            assert engine.pool._max_overflow == overflow
            assert engine.pool.checkedout() == 0
            assert factory.kw['expire_on_commit'] is False
        finally:
            await engine.dispose()
    asyncio.run(scenario())
