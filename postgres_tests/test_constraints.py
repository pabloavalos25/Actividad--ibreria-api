import asyncio
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest

from postgres_tests.helpers import libro, transaction, usuario


@pytest.mark.parametrize('email', ['uno@example.test', 'dos@example.test'])
def test_correo_usuario_unico_y_cliente_vinculo_opcional_unico(pg_config, email):
    async def scenario():
        async with transaction(pg_config) as c:
            uid = await usuario(c, email)
            with pytest.raises(asyncpg.UniqueViolationError):
                async with c.transaction():
                    await usuario(c, email)
            await c.execute(
                "INSERT INTO cliente(nombre,email,usuario_id) VALUES('Uno','c1@example.test',$1)", uid,
            )
            with pytest.raises(asyncpg.UniqueViolationError):
                async with c.transaction():
                    await c.execute(
                        "INSERT INTO cliente(nombre,email,usuario_id) VALUES('Dos','c2@example.test',$1)", uid,
                    )
            await c.execute("INSERT INTO cliente(nombre,email) VALUES('Tres','c3@example.test'),('Cuatro','c4@example.test')")
            assert await c.fetchval('SELECT count(*) FROM cliente WHERE usuario_id IS NULL') == 2
    asyncio.run(scenario())


@pytest.mark.parametrize('missing_user', [999998, 999999])
def test_cliente_rechaza_usuario_inexistente(pg_config, missing_user):
    async def scenario():
        async with transaction(pg_config) as c:
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                async with c.transaction():
                    await c.execute(
                        "INSERT INTO cliente(nombre,email,usuario_id) VALUES('Cliente','c@example.test',$1)", missing_user,
                    )
    asyncio.run(scenario())


@pytest.mark.parametrize('missing', ['libro_id', 'usuario_id', 'venta_id'])
def test_movimiento_rechaza_referencias_inexistentes(pg_config, missing):
    async def scenario():
        async with transaction(pg_config) as c:
            refs = {'libro_id': await libro(c), 'usuario_id': await usuario(c), 'venta_id': None}
            refs[missing] = 999999
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                async with c.transaction():
                    await c.execute(
                        "INSERT INTO movimiento_stock(libro_id,usuario_id,venta_id,cantidad,motivo,cuando) VALUES($1,$2,$3,1,'Prueba',now())",
                        refs['libro_id'], refs['usuario_id'], refs['venta_id'],
                    )
    asyncio.run(scenario())


@pytest.mark.parametrize('precio,stock', [(0, 1), (-1, 1), (1, -1), (1, -2)])
def test_checks_originales_precio_y_stock_siguen_vigentes(pg_config, precio, stock):
    async def scenario():
        async with transaction(pg_config) as c:
            lid = await libro(c)
            with pytest.raises(asyncpg.CheckViolationError):
                async with c.transaction():
                    await c.execute('UPDATE libro SET precio=$1,stock=$2 WHERE id=$3', precio, stock, lid)
            assert await c.fetchval('SELECT stock FROM libro WHERE id=$1', lid) == 3
    asyncio.run(scenario())


@pytest.mark.parametrize('hours', [-3, 5])
def test_fechas_nuevas_conservan_instante_con_zona_y_auditoria_sin_fk(pg_config, hours):
    async def scenario():
        async with transaction(pg_config) as c:
            when = datetime(2026, 11, 5, 12, 30, tzinfo=timezone(timedelta(hours=hours)))
            uid, lid = await usuario(c), await libro(c)
            aid = await c.fetchval(
                "INSERT INTO asignacion_rol(usuario_id,rol,desde,vence_en,revocada_en) VALUES($1,'ADMIN',$2,$2,$2) RETURNING id", uid, when,
            )
            await c.execute('UPDATE libro SET borrado_en=$1 WHERE id=$2', when, lid)
            mid = await c.fetchval(
                "INSERT INTO movimiento_stock(libro_id,usuario_id,cantidad,motivo,cuando) VALUES($1,$2,1,'Prueba',$3) RETURNING id", lid, uid, when,
            )
            iid = await c.fetchval(
                "INSERT INTO intento_acceso(email,ip,cuando,exito) VALUES('no-existe@example.test','::1',$1,false) RETURNING id", when,
            )
            eid = await c.fetchval(
                "INSERT INTO evento_seguridad(actor,accion,cuando) VALUES('SISTEMA','Prueba',$1) RETURNING id", when,
            )
            role = await c.fetchrow('SELECT desde,vence_en,revocada_en FROM asignacion_rol WHERE id=$1', aid)
            assert all(value == when and value.utcoffset() is not None for value in role.values())
            for table, column, identifier in [('libro', 'borrado_en', lid), ('movimiento_stock', 'cuando', mid),
                                               ('intento_acceso', 'cuando', iid), ('evento_seguridad', 'cuando', eid)]:
                # Identificadores internos constantes; los datos siempre ligados.
                stored = await c.fetchval(f'SELECT {column} FROM {table} WHERE id=$1', identifier)
                assert stored == when
                assert stored.utcoffset() is not None
    asyncio.run(scenario())


@pytest.mark.parametrize('rol', ['ADMIN', 'CLIENTE'])
def test_asignacion_abierta_unica_incluso_vencida_y_reasignacion_tras_revocar(pg_config, rol):
    async def scenario():
        async with transaction(pg_config) as c:
            uid = await usuario(c)
            past = datetime.now(timezone.utc) - timedelta(days=1)
            aid = await c.fetchval(
                'INSERT INTO asignacion_rol(usuario_id,rol,desde,vence_en) VALUES($1,$2,$3,$3) RETURNING id',
                uid, rol, past,
            )
            with pytest.raises(asyncpg.UniqueViolationError):
                async with c.transaction():
                    await c.execute('INSERT INTO asignacion_rol(usuario_id,rol,desde) VALUES($1,$2,$3)', uid, rol, past)
            await c.execute('UPDATE asignacion_rol SET revocada_en=$1 WHERE id=$2', datetime.now(timezone.utc), aid)
            await c.execute('INSERT INTO asignacion_rol(usuario_id,rol,desde) VALUES($1,$2,$3)', uid, rol, past)
            assert await c.fetchval('SELECT count(*) FROM asignacion_rol WHERE usuario_id=$1', uid) == 2
    asyncio.run(scenario())


@pytest.mark.parametrize('rol', ['ROOT', 'admin'])
def test_rol_fuera_de_catalogo_rechazado_en_base(pg_config, rol):
    async def scenario():
        async with transaction(pg_config) as c:
            uid = await usuario(c)
            with pytest.raises(asyncpg.CheckViolationError):
                async with c.transaction():
                    await c.execute('INSERT INTO asignacion_rol(usuario_id,rol,desde) VALUES($1,$2,now())', uid, rol)
    asyncio.run(scenario())


@pytest.mark.parametrize('isbn', ['ISBN-A', 'ISBN-B'])
def test_isbn_reutilizable_solo_con_baja_y_reactivacion_conflictiva_rechazada(pg_config, isbn):
    async def scenario():
        async with transaction(pg_config) as c:
            old = await libro(c, isbn)
            editorial = await c.fetchval('SELECT editorial_id FROM libro WHERE id=$1', old)

            async def add():
                return await c.fetchval(
                    'INSERT INTO libro(isbn,titulo,precio,stock,editorial_id) VALUES($1,$2,20,0,$3) RETURNING id',
                    isbn, 'Nueva edición', editorial,
                )

            with pytest.raises(asyncpg.UniqueViolationError):
                async with c.transaction():
                    await add()
            await c.execute('UPDATE libro SET borrado_en=now() WHERE id=$1', old)
            new = await add()
            assert new != old
            with pytest.raises(asyncpg.UniqueViolationError):
                async with c.transaction():
                    await c.execute('UPDATE libro SET borrado_en=NULL WHERE id=$1', old)
            assert await c.fetchval('SELECT count(*) FROM libro WHERE isbn=$1', isbn) == 2
    asyncio.run(scenario())


@pytest.mark.parametrize('cantidad', [4, -2])
def test_movimiento_admite_signos_y_rechaza_cero(pg_config, cantidad):
    async def scenario():
        async with transaction(pg_config) as c:
            uid, lid = await usuario(c), await libro(c)
            mid = await c.fetchval(
                "INSERT INTO movimiento_stock(libro_id,usuario_id,cantidad,motivo,cuando) VALUES($1,$2,$3,'Prueba',now()) RETURNING id",
                lid, uid, cantidad,
            )
            assert await c.fetchval('SELECT cantidad FROM movimiento_stock WHERE id=$1', mid) == cantidad
            with pytest.raises(asyncpg.CheckViolationError):
                async with c.transaction():
                    await c.execute(
                        "INSERT INTO movimiento_stock(libro_id,usuario_id,cantidad,motivo,cuando) VALUES($1,$2,0,'Cero',now())", lid, uid,
                    )
    asyncio.run(scenario())


@pytest.mark.parametrize('target', ['usuario_id', 'otorgada_por'])
def test_asignacion_rechaza_usuarios_inexistentes(pg_config, target):
    async def scenario():
        async with transaction(pg_config) as c:
            uid = await usuario(c)
            owner, grantor = (999999, uid) if target == 'usuario_id' else (uid, 999999)
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                async with c.transaction():
                    await c.execute(
                        "INSERT INTO asignacion_rol(usuario_id,otorgada_por,rol,desde) VALUES($1,$2,'ADMIN',now())", owner, grantor,
                    )
    asyncio.run(scenario())
