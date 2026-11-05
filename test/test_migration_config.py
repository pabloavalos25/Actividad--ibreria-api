import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('jwt_present', [True, False])
def test_alembic_offline_usa_settings_sin_conectar_ni_leer_env_real(tmp_path, jwt_present):
    env = {k: v for k, v in os.environ.items() if not (
        k.startswith(('POSTGRES_', 'JWT_')) or k in {'DATABASE_URL', 'ECHO_SQL', 'SQL_ECHO'}
    )}
    env.update(POSTGRES_USER='test', POSTGRES_PASSWORD='test@:/#?%',
               POSTGRES_DB='test', POSTGRES_HOST='127.0.0.1', POSTGRES_PORT='1')
    if jwt_present:
        env['JWT_SECRET'] = 'test-offline-signature'
    script = (
        'import dotenv; dotenv.load_dotenv=lambda *args, **kwargs: None; '
        'from alembic.config import Config; from alembic import command; '
        f'c=Config({str(ROOT / "alembic.ini")!r}); '
        f'c.set_main_option("script_location", {str(ROOT / "migrations")!r}); '
        'command.upgrade(c,"head",sql=True)'
    )
    result = subprocess.run([sys.executable, '-c', script], env=env, cwd=tmp_path,
                            capture_output=True, text=True)
    if jwt_present:
        assert result.returncode == 0, result.stderr
        assert 'CREATE TABLE libro' in result.stdout
        assert 'COMMIT' in result.stdout
    else:
        assert result.returncode != 0
        assert 'jwt_secret' in result.stderr
    assert env['POSTGRES_PASSWORD'] not in result.stdout + result.stderr
