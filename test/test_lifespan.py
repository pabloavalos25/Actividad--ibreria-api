import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main
from app.core.config import Settings


@pytest.fixture
def settings(monkeypatch):
    result = Settings(
        _env_file=None, postgres_user='test', postgres_password='test-password',
        postgres_db='test', postgres_host='127.0.0.1', postgres_port=1,
        jwt_secret='test-signature', db_pool_size=2, db_max_overflow=0,
        bcrypt_rounds=4, bcrypt_concurrency=2,
    )
    monkeypatch.setattr(main, 'get_settings', lambda: result)
    return result


def test_lifespan_hash_una_vez_y_pool_configurado(settings):
    app = FastAPI(lifespan=main.lifespan)
    app.include_router(main.health_router)
    assert not hasattr(app.state, 'engine')
    assert not hasattr(app.state, 'dummy_password_hash')
    with TestClient(app) as client:
        engine = app.state.engine
        first_hash = app.state.dummy_password_hash
        assert first_hash.startswith('$2b$04$')
        assert engine.pool.size() == 2
        assert engine.pool._max_overflow == 0
        assert app.state.session_factory.kw['expire_on_commit'] is False
        assert client.get('/health/live').status_code == 200
        assert client.get('/health/live').status_code == 200
        assert app.state.dummy_password_hash == first_hash
        assert engine.pool.checkedout() == 0


@pytest.mark.parametrize('failure', ['request', 'hash'])
def test_dispose_tambien_si_falla_peticion_o_hash(monkeypatch, settings, failure):
    async def scenario():
        engine = SimpleNamespace(dispose=AsyncMock())
        monkeypatch.setattr(main, 'create_engine_and_factory', lambda **kwargs: (engine, object()))
        hash_mock = AsyncMock(return_value='hash-ficticio')
        if failure == 'hash':
            hash_mock.side_effect = RuntimeError('fallo hash')
        monkeypatch.setattr(main, 'hash_password', hash_mock)
        app = FastAPI()
        with pytest.raises(RuntimeError, match='fallo'):
            async with main.lifespan(app):
                raise RuntimeError('fallo petición')
        engine.dispose.assert_awaited_once()
        hash_mock.assert_awaited_once()
        password = hash_mock.call_args.args[0]
        assert 0 < len(password.encode('utf-8')) <= 72
        assert hash_mock.call_args.kwargs['rounds'] == settings.bcrypt_rounds
    asyncio.run(scenario())


@pytest.mark.parametrize('missing', ['jwt_secret', 'postgres_password'])
def test_startup_sin_secretos_falla_antes_de_crear_motor(monkeypatch, settings, missing):
    async def scenario():
        values = {
            'postgres_user': 'test', 'postgres_password': 'test-password',
            'postgres_db': 'test', 'postgres_host': 'localhost',
            'jwt_secret': 'test-signature',
        }
        values.pop(missing)
        monkeypatch.delenv(missing.upper(), raising=False)
        monkeypatch.setattr(main, 'get_settings', lambda: Settings(_env_file=None, **values))
        build = Mock()
        monkeypatch.setattr(main, 'create_engine_and_factory', build)
        with pytest.raises(ValidationError):
            async with main.lifespan(FastAPI()):
                pytest.fail('No debe arrancar sin secretos')
        build.assert_not_called()
    asyncio.run(scenario())
