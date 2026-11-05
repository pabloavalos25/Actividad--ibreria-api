from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import asyncpg


@asynccontextmanager
async def transaction(config):
    connection = await asyncpg.connect(**{key: config[key] for key in (
        'host', 'port', 'user', 'password', 'database',
    )})
    try:
        actual = await connection.fetchval('SHOW data_directory')
        assert Path(actual).resolve() == Path(config['data_directory']).resolve(), 'Cluster distinto al autorizado'
        assert await connection.fetchval('SELECT current_database()') == config['database']
        rollback = connection.transaction()
        await rollback.start()
        try:
            yield connection
        finally:
            await rollback.rollback()
    finally:
        await connection.close()


async def usuario(c, email='usuario@example.test'):
    return await c.fetchval(
        'INSERT INTO usuario(email,nombre,password_hash,activo,debe_cambiar_password) '
        'VALUES($1,$2,$3,true,false) RETURNING id', email, 'Usuario', 'hash-de-prueba',
    )


async def libro(c, isbn='ISBN-TEST', *, borrado=False):
    editorial = await c.fetchval(
        "INSERT INTO editorial(nombre,pais) VALUES('Editorial prueba','Argentina') RETURNING id",
    )
    return await c.fetchval(
        'INSERT INTO libro(isbn,titulo,precio,stock,editorial_id,borrado_en) '
        'VALUES($1,$2,10.25,3,$3,$4) RETURNING id',
        isbn, 'Libro prueba', editorial, datetime.now(timezone.utc) if borrado else None,
    )
