"""Verificador reproducible: cluster NUEVO en tmp/, migraciones y tests, apagado final.

No acepta una URL ni un directorio de datos existentes. No lee el .env del proyecto.
Requiere PostgreSQL instalado y las dependencias de requirements-dev.txt.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid

import asyncpg


ROOT = Path(__file__).resolve().parents[1]


async def connect_owned(config, database='postgres'):
    connection = await asyncpg.connect(
        host=config['host'], port=config['port'], user=config['user'],
        password=config['password'], database=database, timeout=5,
    )
    actual = await connection.fetchval('SHOW data_directory')
    if Path(actual).resolve() != Path(config['data_directory']).resolve():
        await connection.close()
        raise RuntimeError('El servidor no pertenece al cluster temporal creado por este proceso')
    return connection


async def create_database(config):
    connection = await connect_owned(config)
    try:
        await connection.execute('CREATE DATABASE parcial_ej2')
    finally:
        await connection.close()


async def verify_base(config):
    connection = await connect_owned(config, config['database'])
    try:
        tables = await connection.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'",
        )
        function = await connection.fetchval("SELECT to_regprocedure('impedir_cambio_movimiento_stock()')")
        if tables or function is not None:
            raise RuntimeError('Downgrade base dejó tablas o la función del trigger')
        print('Downgrade base: sin tablas de dominio ni función de sólo agregado', flush=True)
    finally:
        await connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pg-bin', type=Path, default=Path('C:/Program Files/PostgreSQL/17/bin'))
    args = parser.parse_args()
    executable_suffix = '.exe' if os.name == 'nt' else ''
    binaries = {name: args.pg_bin / (name + executable_suffix) for name in ('initdb', 'pg_ctl')}
    for path in binaries.values():
        if not path.is_file():
            parser.error(f'Falta {path}; indicar --pg-bin con los binarios instalados')

    directory = (ROOT / 'tmp' / f'postgres-tests-{uuid.uuid4().hex[:12]}').resolve()
    if not directory.is_relative_to(ROOT / 'tmp'):
        raise RuntimeError('Directorio temporal fuera del workspace')
    directory.mkdir(parents=True, exist_ok=False)
    data = directory / 'data'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    if port == 5432:
        raise RuntimeError('No se permite el puerto de la base habitual')
    config = {
        'owner': 'parcial-ej2-tests', 'data_directory': str(data),
        'host': '127.0.0.1', 'port': port, 'user': 'parcial_test',
        'password': 'test-only-password', 'database': 'parcial_ej2',
    }
    config_file = directory / 'connection.json'
    config_file.write_text(json.dumps(config, indent=2), encoding='utf-8')
    environment = {key: value for key, value in os.environ.items() if not (
        key.startswith(('POSTGRES_', 'JWT_', 'BCRYPT_', 'PG'))
        or key in {'DATABASE_URL', 'ECHO_SQL', 'SQL_ECHO'}
    )}
    environment.update(
        POSTGRES_USER=config['user'], POSTGRES_PASSWORD=config['password'],
        POSTGRES_DB=config['database'], POSTGRES_HOST=config['host'], POSTGRES_PORT=str(port),
        JWT_SECRET='test-only-signature', BCRYPT_ROUNDS='4', BCRYPT_CONCURRENCY='2', SQL_ECHO='false',
        PYTHONPATH=str(ROOT),
    )

    def run(command):
        # PostgreSQL se desprende de pg_ctl. Usar archivo, no PIPE, evita que
        # un handle heredado del servidor mantenga communicate() esperando EOF.
        command_log = directory / 'command.log'
        with command_log.open('w', encoding='utf-8') as output_file:
            result = subprocess.run(
                command, cwd=directory, env=environment, stdout=output_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
        output = command_log.read_text(encoding='utf-8', errors='replace')
        print(output, end='', flush=True)
        with (directory / 'verification.log').open('a', encoding='utf-8') as log:
            log.write(output)
        result.check_returncode()

    def alembic(action, target=None):
        code = (
            f'import sys; sys.path.insert(0, {str(ROOT / ".venv/Lib/site-packages")!r}); '
            'from alembic.config import Config; from alembic import command; '
            f'c=Config({str(ROOT / "alembic.ini")!r}); '
            f'c.set_main_option("script_location", {str(ROOT / "migrations")!r}); '
            f'command.{action}(c{", " + repr(target) if target else ""})'
        )
        run([sys.executable, '-c', code])

    print(f'Cluster nuevo: {directory}; dirección 127.0.0.1:{port}', flush=True)
    initialized = False
    try:
        run([str(binaries['initdb']), '-D', str(data), '-U', config['user'],
             '--auth=trust', '--encoding=UTF8', '--no-locale'])
        initialized = True
        run([str(binaries['pg_ctl']), '-D', str(data), '-l', str(directory / 'server.log'),
             '-o', f'-h 127.0.0.1 -p {port} -c max_connections=20', '-w', 'start'])
        asyncio.run(create_database(config))
        alembic('upgrade', 'head')
        alembic('check')
        alembic('downgrade', 'base')
        asyncio.run(verify_base(config))
        alembic('upgrade', 'head')
        alembic('check')
        pytest_args = ['pytest', str(ROOT / 'postgres_tests'), '-q', '--postgres-config',
                       str(config_file), '--basetemp', str(directory / 'pytest-online'),
                       '-o', f'cache_dir={directory / "pytest-cache"}']
        # También permite el Python embebido de pgAdmin, que ignora PYTHONPATH.
        # Sólo se usan las dependencias instaladas localmente; no se modifica
        # el intérprete ni sus site-packages globales.
        run([sys.executable, '-c',
             f'import sys,runpy; sys.path.insert(0,{str(ROOT)!r}); '
             f'sys.path.insert(0,{str(ROOT / ".venv/Lib/site-packages")!r}); '
             f'sys.argv={pytest_args!r}; runpy.run_module("pytest",run_name="__main__")'])
    finally:
        # Sólo el data_directory NUEVO creado por esta invocación; nunca PGDATA
        # heredado, servicio del sistema, directorio existente o proceso ajeno.
        if initialized and (data / 'postmaster.pid').is_file():
            run([str(binaries['pg_ctl']), '-D', str(data), '-m', 'fast', '-w', 'stop'])
        if (data / 'postmaster.pid').exists():
            raise RuntimeError(f'El cluster propio no se detuvo: {data}')
        print(f'Cluster propio detenido; logs conservados en {directory}', flush=True)


if __name__ == '__main__':
    main()
