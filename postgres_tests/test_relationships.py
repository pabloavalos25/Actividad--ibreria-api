import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import URL, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.ventas.models import Venta


@pytest.mark.parametrize('with_sale', [False, True])
def test_grafo_orm_persistido_y_libro_borrado_conserva_historial(pg_config, with_sale):
    async def scenario():
        url = URL.create('postgresql+asyncpg', username=pg_config['user'], password=pg_config['password'],
                         host=pg_config['host'], port=pg_config['port'], database=pg_config['database'])
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                actual = await connection.scalar(text('SHOW data_directory'))
                assert Path(actual).resolve() == Path(pg_config['data_directory']).resolve()
                async with AsyncSession(connection, expire_on_commit=False) as session:
                    usuario = Usuario(email='orm@example.test', nombre='Usuario', password_hash='hash')
                    otorgante = Usuario(email='admin@example.test', nombre='Admin', password_hash='hash')
                    cliente = Cliente(nombre='Cliente', email='cliente@example.test', usuario=usuario)
                    editorial = Editorial(nombre='Editorial ORM', pais='Argentina')
                    libro = Libro(isbn='ISBN-ORM', titulo='Título histórico', precio=Decimal('10.25'),
                                  stock=3, editorial=editorial)
                    venta = Venta(cliente=cliente, total=Decimal('10.25')) if with_sale else None
                    asignacion = AsignacionRol(usuario=usuario, otorgante=otorgante, rol='CLIENTE')
                    movimiento = MovimientoStock(libro=libro, usuario=usuario, venta=venta,
                                                 cantidad=-1 if with_sale else 3, motivo='Prueba ORM')
                    session.add_all([cliente, asignacion, movimiento])
                    await session.flush()
                    mid, uid = movimiento.id, usuario.id
                    libro.borrado_en = datetime.now(timezone.utc)
                    await session.flush()
                    session.expunge_all()
                    result = await session.execute(select(MovimientoStock).where(MovimientoStock.id == mid).options(
                        selectinload(MovimientoStock.libro), selectinload(MovimientoStock.venta),
                        selectinload(MovimientoStock.usuario).selectinload(Usuario.cliente),
                    ))
                    loaded = result.scalar_one()
                    assert loaded.libro.titulo == 'Título histórico'
                    assert loaded.libro.borrado_en is not None
                    assert loaded.libro.precio == Decimal('10.25')
                    assert loaded.usuario.id == uid
                    assert loaded.usuario.cliente.usuario_id == uid
                    assert (loaded.venta is not None) is with_sale
                    role = (await session.execute(select(AsignacionRol).options(
                        selectinload(AsignacionRol.usuario), selectinload(AsignacionRol.otorgante),
                    ))).scalar_one()
                    assert role.usuario.email == 'orm@example.test'
                    assert role.otorgante.email == 'admin@example.test'
                await connection.rollback()
        finally:
            await engine.dispose()
    asyncio.run(scenario())
