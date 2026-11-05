"""Caracterización del TP antes de modificar configuración/ciclo de vida."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import create_engine_and_factory, get_session
from app.modules.health.router import router


def test_live_no_pide_sesion():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.get('/health/live')
    assert response.status_code == 200
    assert response.json() == {'estado': 'vivo'}


@pytest.mark.parametrize('disponible', [True, False])
def test_ready_consulta_la_base_y_no_expone_errores(disponible):
    session = SimpleNamespace(execute=AsyncMock())
    if not disponible:
        session.execute.side_effect = RuntimeError('detalle interno sensible')
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get('/health/ready')
    assert str(session.execute.call_args.args[0]) == 'SELECT 1'
    assert session.execute.await_count == 1
    assert response.status_code == (200 if disponible else 503)
    assert response.json() == (
        {'estado': 'ok', 'base': 'disponible'} if disponible
        else {'detail': 'Base de datos no disponible'}
    )


def test_fabrica_no_expira_al_confirmar_y_no_conecta_al_crearse():
    async def scenario():
        engine, factory = create_engine_and_factory(
            'postgresql+asyncpg://test:test@127.0.0.1:1/test'
        )
        assert factory.kw['expire_on_commit'] is False
        assert engine.pool.checkedout() == 0
        async with factory() as first, factory() as second:
            assert first is not second
        await engine.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize('fallo', [False, True])
def test_get_session_cierra_una_sesion_por_peticion(fallo):
    async def scenario():
        closed = []

        class TrackingSession(AsyncSession):
            async def close(self):
                closed.append(self)
                await super().close()

        app = FastAPI()
        app.state.session_factory = async_sessionmaker(class_=TrackingSession)
        request = Request({'type': 'http', 'app': app})
        generator = get_session(request)
        session = await anext(generator)
        assert closed == []
        if fallo:
            with pytest.raises(RuntimeError, match='fallo de petición'):
                await generator.athrow(RuntimeError('fallo de petición'))
        else:
            await generator.aclose()
        assert closed == [session]
    asyncio.run(scenario())


def test_lifespan_crea_recursos_al_arrancar_y_cierra_al_apagar(monkeypatch):
    from app import main

    async def scenario():
        engine = SimpleNamespace(dispose=AsyncMock())
        factory = object()
        calls = []
        monkeypatch.setattr(main, 'get_settings', lambda: SimpleNamespace(
            database_url='postgresql+asyncpg://test:test@localhost/test', echo_sql=False,
            db_pool_size=5, db_max_overflow=10, bcrypt_rounds=4, bcrypt_concurrency=1,
        ))

        def build(**kwargs):
            calls.append(kwargs)
            return engine, factory

        monkeypatch.setattr(main, 'create_engine_and_factory', build)
        app = FastAPI()
        assert calls == []
        async with main.lifespan(app):
            assert len(calls) == 1
            assert app.state.engine is engine
            assert app.state.session_factory is factory
            engine.dispose.assert_not_awaited()
        engine.dispose.assert_awaited_once()
    asyncio.run(scenario())
