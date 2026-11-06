"""C-15: consultas medidas, identidades vacías y DTO sin sesión disponible."""

import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import event, select

from postgres_tests.test_auth import api, account
from app.modules.autores.models import Autor
from app.modules.autores.repository import AutorRepository
from app.modules.autores.schemas import LibroConRol
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.repository import ClienteRepository
from app.modules.clientes.schemas import ClienteRead
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.repository import LibroRepository
from app.modules.libros.schemas import LibroRead
from app.modules.libros.service import detalle
from app.modules.usuarios.models import AsignacionRol
from app.modules.ventas.models import Venta, RenglonVenta
from app.modules.ventas.repository import VentaRepository
from app.modules.ventas.service import a_read


@contextmanager
def select_statements(engine):
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            statements.append(statement)

    event.listen(engine.sync_engine, 'before_cursor_execute', record)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, 'before_cursor_execute', record)


async def catalog(factory, customer_id, *, optional=True):
    async with factory.begin() as session:
        editorial = Editorial(nombre='Editorial C15', pais='AR')
        genre = Genero(nombre='Género C15')
        author = Autor(nombre='Autor C15', nacionalidad='AR')
        session.add_all([editorial, genre, author])
        await session.flush()
        books = []
        for index in range(4):
            book = Libro(isbn=f'c15-{index}', titulo=f'Libro C15 {index}', precio=Decimal('12.50'),
                         stock=10, editorial_id=editorial.id, genero_id=genre.id if optional else None,
                         autorias=[LibroAutor(autor_id=author.id, rol='autor', orden=1)])
            session.add(book)
            books.append(book)
        if optional:
            session.add(PerfilCliente(cliente_id=customer_id, telefono='123', direccion='Calle C15'))
        await session.flush()
        return dict(editorial=editorial.id, genre=genre.id, author=author.id,
                    books=[book.id for book in books])


def test_c15_detalle_dos_y_cuatro_renglones_consultas_constantes(pg_config):
    async def scenario():
        from app.main import app as configured

        async with api(pg_config) as (client, factory, app):
            app.router.routes = list(configured.router.routes)
            data = account()
            user_id = (await client.post('/auth/registro', json=data)).json()['id']
            async with factory.begin() as session:
                session.add(AsignacionRol(usuario_id=user_id, rol='ADMIN'))
                customer_id = await session.scalar(select(Cliente.id).where(Cliente.usuario_id == user_id))
            ids = await catalog(factory, customer_id)
            sales = []
            async with factory.begin() as session:
                for size in (2, 4):
                    sale = Venta(cliente_id=customer_id, total=Decimal('12.50') * size,
                                 renglones=[RenglonVenta(libro_id=book_id, cantidad=1,
                                            precio_unitario=Decimal('12.50')) for book_id in ids['books'][:size]])
                    session.add(sale)
                    await session.flush()
                    sales.append(sale.id)
                book = await session.get(Libro, ids['books'][0])
                book.borrado_en = datetime.now(timezone.utc)
            login = await client.post('/auth/login', json={key: data[key] for key in ('email', 'password')})
            assert login.status_code == 200, login.text
            engine = factory.kw['bind']
            measurements = []
            for size, sale_id in zip((2, 4), sales):
                with select_statements(engine) as repository_sql:
                    async with factory() as session:
                        assert len(session.identity_map) == 0
                        sale = await VentaRepository(session).con_cliente_renglones_libros(sale_id)
                    count_before = len(repository_sql)
                    result = a_read(sale).model_dump(mode='json')
                    assert len(repository_sql) == count_before == 2
                assert result['cliente']['id'] == customer_id
                assert len(result['renglones']) == size
                assert [row['titulo'] for row in result['renglones']] == [f'Libro C15 {i}' for i in range(size)]
                assert Decimal(result['total']) == Decimal('12.50') * size
                with select_statements(engine) as http_sql:
                    response = await client.get(f'/ventas/{sale_id}')
                    assert response.status_code == 200, response.text
                    assert response.json() == result
                categories = {
                    'usuario': sum('FROM usuario ' in sql for sql in http_sql),
                    'roles': sum('FROM asignacion_rol ' in sql for sql in http_sql),
                    'detalle': sum('FROM venta ' in sql or 'FROM renglon_venta ' in sql for sql in http_sql),
                }
                assert categories == {'usuario': 1, 'roles': 1, 'detalle': 2}
                assert len(http_sql) == sum(categories.values())
                measurements.append((size, repository_sql, http_sql, categories))
            assert len(measurements[0][1]) == len(measurements[1][1])
            assert len(measurements[0][2]) == len(measurements[1][2])
            for filters in ({}, {'cliente_id': customer_id}, {'usuario_id': user_id}):
                with select_statements(engine) as statements:
                    async with factory() as session:
                        assert not session.identity_map
                        page = await VentaRepository(session).con_detalles(1, 20, **filters)
                    count = len(statements)
                    values = [a_read(sale) for sale in page['items']]
                    assert len(statements) == count == 3
                    assert page['total'] == len(values) == 2
                    assert [len(sale.renglones) for sale in values] == [2, 4]
                    assert all(sale.renglones[0].titulo == 'Libro C15 0' for sale in values)
            lines = ['C-15: PostgreSQL real; sólo SELECT dentro de cada ventana de lectura.',
                     'Sesiones de repositorio nuevas, sin identity map; DTO serializado tras cierre.',
                     'HTTP con cookie real, sin overrides de autenticación; incluye usuario y roles.',
                     'Los dos tamaños incluyen Libro C15 0 dado de baja después de vender.',
                     'SQL sin valores de parámetros; no incluye preparación de datos ni login.']
            for size, repository_sql, http_sql, categories in measurements:
                lines.extend(['', f'Renglones={size}; repositorio={len(repository_sql)}; '
                              f'HTTP={len(http_sql)}; categorías={categories}; serialización=0 SELECT.'])
                for index, statement in enumerate(http_sql, 1):
                    lines.extend([f'HTTP SELECT {index}:', statement])
            output = Path(pg_config['data_directory']).parent / 'c15_consultas.txt'
            output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    asyncio.run(scenario())


@pytest.mark.parametrize('optional', [False, True])
def test_otras_relaciones_de_salida_sin_sesion(pg_config, optional):
    async def scenario():
        async with api(pg_config) as (client, factory, app):
            data = account()
            user_id = (await client.post('/auth/registro', json=data)).json()['id']
            async with factory() as session:
                customer_id = await session.scalar(select(Cliente.id).where(Cliente.usuario_id == user_id))
            ids = await catalog(factory, customer_id, optional=optional)
            engine = factory.kw['bind']
            with select_statements(engine) as statements:
                async with factory() as session:
                    assert not session.identity_map
                    book = await LibroRepository(session).con_detalle(ids['books'][0])
                count = len(statements)
                value = detalle(book)
                assert len(statements) == count
                assert value.editorial.nombre == 'Editorial C15'
                assert (value.genero is not None) is optional
                assert value.autores[0].nombre == 'Autor C15'
            filters_to_check = [{}, {'editorial_id': ids['editorial']}]
            if optional:
                filters_to_check.append({'genero_id': ids['genre']})
            for filters in filters_to_check:
                with select_statements(engine) as statements:
                    async with factory() as session:
                        assert not session.identity_map
                        page = await LibroRepository(session).catalogo(1, 20, **filters)
                    count = len(statements)
                    values = [LibroRead.model_validate(book) for book in page['items']]
                    assert len(statements) == count
                    assert page['total'] == len(values) == 4
                    assert all(value.editorial.nombre == 'Editorial C15' for value in values)
                    assert all((value.genero is not None) is optional for value in values)
            with select_statements(engine) as statements:
                async with factory() as session:
                    assert not session.identity_map
                    page = await AutorRepository(session).libros_con_autoria(ids['author'], 1, 20)
                count = len(statements)
                values = [LibroConRol(libro_id=row.libro_id, isbn=row.libro.isbn, titulo=row.libro.titulo,
                          precio=row.libro.precio, stock=row.libro.stock, rol=row.rol, orden=row.orden)
                          for row in page['items']]
                assert len(statements) == count
                assert len(values) == 4 and all(value.rol == 'autor' for value in values)
            with select_statements(engine) as statements:
                async with factory() as session:
                    assert not session.identity_map
                    customer = await ClienteRepository(session).con_perfil(customer_id)
                count = len(statements)
                value = ClienteRead.model_validate(customer)
                assert len(statements) == count
                assert value.email == data['email']
                assert (value.perfil is not None) is optional
                if optional:
                    assert value.perfil.telefono == '123'
    asyncio.run(scenario())
