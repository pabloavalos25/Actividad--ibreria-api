import importlib.util
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError

import pytest


SHELL = shutil.which('sh') or ('C:/Program Files/Git/bin/sh.exe' if os.name == 'nt' else None)


def start_with_commands(tmp_path, database_url, migration_exit=0, *, deploy_dir):
    entrypoint = deploy_dir / 'docker-entrypoint.sh'
    assert entrypoint.is_file(), 'Falta el entrypoint de contenedor'
    assert SHELL, 'Estas pruebas requieren shell POSIX'
    commands = tmp_path / 'bin'
    commands.mkdir()
    trace = tmp_path / 'commands.txt'
    for name, exit_code in [('alembic', migration_exit), ('uvicorn', 0)]:
        command = commands / name
        command.write_text(
            '#!/bin/sh\nprintf "%s\\n" "' + name + ' $*" >> "$TRACE"\nexit ' + str(exit_code) + '\n',
            encoding='utf-8', newline='\n',
        )
        command.chmod(0o755)
    env = os.environ.copy()
    env.pop('DATABASE_URL', None)
    if database_url is not None:
        env['DATABASE_URL'] = database_url
    env['TRACE'] = trace.as_posix()
    # MSYS PATH needs /c/... rather than a Windows drive colon.
    setup = 'commands="$1"; '
    if os.name == 'nt':
        setup += 'commands=$(cygpath -u "$commands"); '
    setup += 'PATH="$commands:$PATH"; export PATH; exec /bin/sh "$2"'
    completed = subprocess.run(
        [SHELL, '-c', setup, 'entrypoint-test', commands.as_posix(), entrypoint.as_posix()],
        env=env, capture_output=True, text=True, timeout=10,
    )
    return completed, trace.read_text().splitlines() if trace.exists() else []


@pytest.mark.parametrize('url', ['postgresql+asyncpg://one/db', 'postgresql+asyncpg://two/db'])
def test_entrypoint_migra_antes_de_servidor(tmp_path, url, deploy_dir):
    result, commands = start_with_commands(tmp_path, url, deploy_dir=deploy_dir)
    assert result.returncode == 0, result.stderr
    assert commands == ['alembic upgrade head', 'uvicorn app.main:app --host 0.0.0.0 --port 8000']
    assert b'\r' not in (deploy_dir / 'docker-entrypoint.sh').read_bytes()


@pytest.mark.parametrize('exit_code', [7, 42])
def test_migracion_fallida_o_base_inaccesible_impide_servidor(tmp_path, exit_code, deploy_dir):
    result, commands = start_with_commands(
        tmp_path, 'postgresql+asyncpg://unreachable/db', exit_code, deploy_dir=deploy_dir,
    )
    assert result.returncode == exit_code
    assert commands == ['alembic upgrade head']


@pytest.mark.parametrize('url', [None, ''])
def test_url_ausente_o_vacia_falla_antes_de_migrar(tmp_path, url, deploy_dir):
    result, commands = start_with_commands(tmp_path, url, deploy_dir=deploy_dir)
    assert result.returncode != 0
    assert 'DATABASE_URL' in result.stderr
    assert commands == []


def load_healthcheck(deploy_dir):
    healthcheck = deploy_dir / 'healthcheck.py'
    assert healthcheck.is_file(), 'Falta el healthcheck de contenedor'
    spec = importlib.util.spec_from_file_location('container_healthcheck', healthcheck)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('status,expected', [(200, 0), (503, 1)])
def test_healthcheck_http_real(status, expected, deploy_dir):
    module = load_healthcheck(deploy_dir)
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b'{}')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert module.check_ready(f'http://127.0.0.1:{server.server_port}/health/ready') == expected
        assert requests == ['/health/ready']
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize('error', [TimeoutError('slow'), URLError('refused')])
def test_healthcheck_timeout_y_conexion_fallida_no_son_saludables(monkeypatch, error, deploy_dir):
    module = load_healthcheck(deploy_dir)
    calls = []

    def fail(url, *, timeout):
        calls.append((url, timeout))
        raise error

    monkeypatch.setattr(module, 'urlopen', fail)
    assert module.check_ready() == 1
    assert calls == [('http://127.0.0.1:8000/health/ready', 2)]
