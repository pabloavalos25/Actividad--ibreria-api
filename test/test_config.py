import os

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.core.config import Settings


def test_settings_compone_url_desde_entorno_sin_romper_password(monkeypatch):
    values = {
        'POSTGRES_USER': 'tester', 'POSTGRES_PASSWORD': 'clave@:/#?%',
        'POSTGRES_DB': 'libreria_test', 'POSTGRES_HOST': '127.0.0.1',
        'POSTGRES_PORT': '5544', 'JWT_SECRET': 'clave-de-prueba-no-real',
        'DB_POOL_SIZE': '3', 'DB_MAX_OVERFLOW': '2', 'SQL_ECHO': 'true',
        'BCRYPT_ROUNDS': '4', 'BCRYPT_CONCURRENCY': '2',
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    settings = Settings(_env_file=None)
    url = make_url(settings.database_url)
    assert url.drivername == 'postgresql+asyncpg'
    assert url.username == 'tester'
    assert url.password == values['POSTGRES_PASSWORD']
    assert (url.host, url.port, url.database) == ('127.0.0.1', 5544, 'libreria_test')
    assert settings.db_pool_size == 3
    assert settings.db_max_overflow == 2
    assert settings.echo_sql is True
    assert settings.bcrypt_rounds == 4
    assert settings.bcrypt_concurrency == 2
    assert values['POSTGRES_PASSWORD'] not in repr(settings)
    assert values['JWT_SECRET'] not in repr(settings)


@pytest.fixture
def settings_values(monkeypatch):
    for key in list(os.environ):
        if key.startswith(('POSTGRES_', 'DB_', 'BCRYPT_', 'JWT_')) or key in {'SQL_ECHO', 'ECHO_SQL'}:
            monkeypatch.delenv(key)
    return {
        'postgres_user': 'otro', 'postgres_password': 'password-de-prueba',
        'postgres_db': 'otra_base', 'postgres_host': 'db.example.test',
        'jwt_secret': 'firma-de-prueba',
    }


def test_settings_otra_configuracion_y_defaults_no_secretos(settings_values):
    settings = Settings(_env_file=None, **settings_values)
    url = make_url(settings.database_url)
    assert (url.host, url.port, url.username, url.database) == (
        'db.example.test', 5432, 'otro', 'otra_base',
    )
    assert settings.echo_sql is False
    assert (settings.db_pool_size, settings.db_max_overflow) == (5, 10)
    assert (settings.bcrypt_rounds, settings.bcrypt_concurrency) == (12, 4)


@pytest.mark.parametrize('field', ['postgres_password', 'jwt_secret'])
@pytest.mark.parametrize('value', [None, ''])
def test_secretos_son_obligatorios_y_no_aceptan_vacios(settings_values, field, value):
    if value is None:
        settings_values.pop(field)
    else:
        settings_values[field] = value
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=None, **settings_values)
    assert field in str(caught.value)
    for secret in ('password-de-prueba', 'firma-de-prueba'):
        assert secret not in str(caught.value)


@pytest.mark.parametrize('field,value', [
    ('db_pool_size', 0), ('db_max_overflow', -1), ('postgres_port', 0),
    ('postgres_port', 65536), ('bcrypt_rounds', 3), ('bcrypt_rounds', 32),
    ('bcrypt_concurrency', 0),
])
def test_parametros_fuera_de_rango_fallan_al_cargar(settings_values, field, value):
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=None, **(settings_values | {field: value}))
    assert field in str(caught.value)
    assert settings_values['postgres_password'] not in str(caught.value)


def test_archivo_entorno_y_variables_del_proceso_tienen_precedencia(tmp_path, monkeypatch, settings_values):
    env_file = tmp_path / 'test.env'
    env_file.write_text('\n'.join(f'{k.upper()}={v}' for k, v in settings_values.items()), encoding='utf-8')
    monkeypatch.setenv('POSTGRES_HOST', 'host-del-proceso.test')
    monkeypatch.setenv('ECHO_SQL', 'true')
    settings = Settings(_env_file=env_file)
    assert make_url(settings.database_url).host == 'host-del-proceso.test'
    assert settings.echo_sql is True
    assert settings.jwt_secret.get_secret_value() == settings_values['jwt_secret']
