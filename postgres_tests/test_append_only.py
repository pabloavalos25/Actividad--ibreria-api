import asyncio
import os
from pathlib import Path
import subprocess

import asyncpg
import pytest

from postgres_tests.helpers import libro, transaction, usuario
from scripts.test_postgres import connect_owned


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('cantidad', [3, -1])
@pytest.mark.parametrize('trigger_habilitado', [True, False])
def test_c14_psql_verifica_rechazos_y_detecta_trigger_ausente(pg_config, cantidad, trigger_habilitado):
    async def scenario():
        c = await connect_owned(pg_config, pg_config['database'])
        try:
            uid, lid = await usuario(c), await libro(c)
            mid = await c.fetchval(
                "INSERT INTO movimiento_stock(libro_id,usuario_id,cantidad,motivo,cuando) "
                "VALUES($1,$2,$3,'Original',now()) RETURNING id", lid, uid, cantidad,
            )
            original = dict(await c.fetchrow('SELECT * FROM movimiento_stock WHERE id=$1', mid))
            if not trigger_habilitado:
                await c.execute('ALTER TABLE movimiento_stock DISABLE TRIGGER trg_movimiento_stock_solo_agregado')
            bindir = Path(await c.fetchval("SELECT setting FROM pg_config WHERE name='BINDIR'"))
            psql = bindir / ('psql.exe' if os.name == 'nt' else 'psql')
            command = [str(psql), '-X', '--no-password', '-h', pg_config['host'], '-p', str(pg_config['port']),
                       '-U', pg_config['user'], '-d', pg_config['database'],
                       '-v', f'movimiento_id={mid}', '-f', 'test/solo_agregado.sql']
            environment = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
            environment['PGCLIENTENCODING'] = 'UTF8'
            result = await asyncio.to_thread(subprocess.run, command, cwd=ROOT, env=environment,
                capture_output=True, text=True, encoding='utf-8', timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            transcript = result.stdout + result.stderr
            log = Path(pg_config['data_directory']).parent / f'c14_{cantidad}_{trigger_habilitado}.log'
            log.write_text(transcript, encoding='utf-8')
            if trigger_habilitado:
                assert result.returncode == 0, transcript
                assert 'C14_UPDATE_SQLSTATE 23514' in transcript
                assert 'C14_DELETE_SQLSTATE 23514' in transcript
                assert 'C14_OK: movimiento intacto' in transcript
            else:
                assert result.returncode != 0, transcript
                assert 'C14_FALLO: UPDATE fue aceptado o rechazo inesperado' in transcript
            assert dict(await c.fetchrow('SELECT * FROM movimiento_stock WHERE id=$1', mid)) == original
        finally:
            # Sólo el cluster propio validado por connect_owned; se restaura aun
            # si falla la prueba metamorfa que deshabilita el trigger.
            await c.execute('ALTER TABLE movimiento_stock ENABLE TRIGGER trg_movimiento_stock_solo_agregado')
            await c.execute('TRUNCATE usuario, libro, editorial RESTART IDENTITY CASCADE')
            await c.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('operation', ['UPDATE', 'UPDATE_SIN_CAMBIOS', 'DELETE'])
@pytest.mark.parametrize('cantidad', [3, -1])
def test_sql_directo_rechaza_cambios_y_conserva_movimiento(pg_config, operation, cantidad):
    async def scenario():
        async with transaction(pg_config) as c:
            uid, lid = await usuario(c), await libro(c)
            mid = await c.fetchval(
                "INSERT INTO movimiento_stock(libro_id,usuario_id,cantidad,motivo,cuando) VALUES($1,$2,$3,'Original',now()) RETURNING id",
                lid, uid, cantidad,
            )
            query = {
                'UPDATE': "UPDATE movimiento_stock SET motivo='Alterado' WHERE id=$1",
                'UPDATE_SIN_CAMBIOS': 'UPDATE movimiento_stock SET motivo=motivo WHERE id=$1',
                'DELETE': 'DELETE FROM movimiento_stock WHERE id=$1',
            }[operation]
            with pytest.raises(asyncpg.CheckViolationError, match='solo agregado'):
                async with c.transaction():
                    await c.execute(query, mid)
            row = await c.fetchrow('SELECT cantidad,motivo FROM movimiento_stock WHERE id=$1', mid)
            assert dict(row) == {'cantidad': cantidad, 'motivo': 'Original'}
    asyncio.run(scenario())
