import asyncio

import asyncpg
import pytest

from postgres_tests.helpers import libro, transaction, usuario


@pytest.mark.parametrize('operation', ['UPDATE', 'DELETE'])
@pytest.mark.parametrize('cantidad', [3, -1])
def test_sql_directo_rechaza_cambios_y_conserva_movimiento(pg_config, operation, cantidad):
    async def scenario():
        async with transaction(pg_config) as c:
            uid, lid = await usuario(c), await libro(c)
            mid = await c.fetchval(
                "INSERT INTO movimiento_stock(libro_id,usuario_id,cantidad,motivo,cuando) VALUES($1,$2,$3,'Original',now()) RETURNING id",
                lid, uid, cantidad,
            )
            query = (
                'UPDATE movimiento_stock SET motivo=motivo WHERE id=$1'
                if operation == 'UPDATE' else 'DELETE FROM movimiento_stock WHERE id=$1'
            )
            with pytest.raises(asyncpg.CheckViolationError, match='solo agregado'):
                async with c.transaction():
                    await c.execute(query, mid)
            row = await c.fetchrow('SELECT cantidad,motivo FROM movimiento_stock WHERE id=$1', mid)
            assert dict(row) == {'cantidad': cantidad, 'motivo': 'Original'}
    asyncio.run(scenario())
