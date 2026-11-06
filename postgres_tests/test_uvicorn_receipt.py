"""Comprobante visible con uvicorn normal y PostgreSQL propio; sin mocks de log."""

import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys

import bcrypt
import httpx
import pytest

from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.usuarios.models import AsignacionRol, Usuario
from postgres_tests.test_auth import api


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('cantidad', [1, 2])
def test_comprobante_visible_con_uvicorn_normal(pg_config, tmp_path, cantidad):
    async def scenario():
        async with api(pg_config) as (_, factory, _):
            # La fixture valida el destino temporal y limpia los commits reales.
            async with factory.begin() as session:
                admin = Usuario(nombre='Admin comprobante', email='comprobante-admin@example.com',
                    password_hash=bcrypt.hashpw(b'abcdefgh', bcrypt.gensalt(rounds=4)).decode())
                editorial = Editorial(nombre='Editorial comprobante', pais='AR')
                cliente = Cliente(nombre='Destino comprobante', email='destino-comprobante@example.com')
                session.add_all([admin, editorial, cliente])
                await session.flush()
                session.add(AsignacionRol(usuario_id=admin.id, rol='ADMIN'))
                editorial_id, cliente_id = editorial.id, cliente.id

            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            environment = {key: value for key, value in os.environ.items() if not (
                key.startswith(('POSTGRES_', 'JWT_', 'BCRYPT_', 'PG'))
                or key in {'DATABASE_URL', 'SQL_ECHO', 'ECHO_SQL', 'COOKIE_SECURE'}
            )}
            environment.update(
                POSTGRES_USER=pg_config['user'], POSTGRES_PASSWORD=pg_config['password'],
                POSTGRES_DB=pg_config['database'], POSTGRES_HOST=pg_config['host'],
                POSTGRES_PORT=str(pg_config['port']), SQL_ECHO='false', COOKIE_SECURE='false',
                JWT_SECRET='test-only-uvicorn-signature-longer-than-32-bytes',
                BCRYPT_ROUNDS='4', BCRYPT_CONCURRENCY='2',
                PYTHONPATH=str(ROOT), PYTHONIOENCODING='utf-8',
            )
            command = [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host',
                       '127.0.0.1', '--port', str(port)]
            log_path = tmp_path / 'uvicorn.log'
            with log_path.open('w', encoding='utf-8') as output:
                process = subprocess.Popen(command, cwd=tmp_path, env=environment,
                    stdout=output, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                try:
                    async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}', timeout=5) as client:
                        for _ in range(150):
                            assert process.poll() is None, log_path.read_text(encoding='utf-8')
                            try:
                                if (await client.get('/health/ready')).status_code == 200:
                                    break
                            except httpx.TransportError:
                                pass
                            await asyncio.sleep(0.1)
                        else:
                            pytest.fail('uvicorn no quedo listo: ' + log_path.read_text(encoding='utf-8'))
                        response = await client.post('/auth/login', json=dict(
                            email='comprobante-admin@example.com', password='abcdefgh'))
                        assert response.status_code == 200, response.text
                        book = await client.post('/libros/', json=dict(isbn='uvicorn-comprobante',
                            titulo='Libro comprobante', precio='12.50', stock_inicial=5,
                            editorial_id=editorial_id))
                        assert book.status_code == 201, book.text
                        response = await client.post('/ventas/', json=dict(cliente_id=cliente_id,
                            renglones=[dict(libro_id=book.json()['id'], cantidad=cantidad)]))
                        assert response.status_code == 201, response.text
                        sale = response.json()
                        expected = (f"Comprobante de venta #{sale['id']} enviado a "
                            f"destino-comprobante@example.com (total {sale['total']})")
                        for _ in range(100):
                            log = log_path.read_text(encoding='utf-8')
                            if expected in log:
                                break
                            await asyncio.sleep(0.05)
                        else:
                            pytest.fail('Falta comprobante visible en log normal: ' + log)
                        assert log.count(expected) == 1
                        assert log.index('"POST /ventas/ HTTP/1.1" 201 Created') < log.index(expected)
                        print(f'UVICORN_EVIDENCE_LOG={log_path}')
                        print(log)
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    assert process.poll() is not None

    asyncio.run(scenario())
