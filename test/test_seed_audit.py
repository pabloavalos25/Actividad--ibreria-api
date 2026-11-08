import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from types import SimpleNamespace

import pytest
import seed
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.ventas.models import Venta


@pytest.mark.parametrize('fail', [False, True])
def test_seed_evento_sistema_antes_commit(fail):
    async def scenario():
        events = []
        def add(entity):
            if isinstance(entity, EventoSeguridad):
                events.append(entity)
        session = SimpleNamespace(execute=AsyncMock(), add=Mock(side_effect=add), flush=AsyncMock(), commit=AsyncMock())
        if fail:
            session.commit.side_effect = RuntimeError('rollback esperado por dueño de sesión')
            with pytest.raises(RuntimeError):
                await seed.cargar(session)
        else:
            await seed.cargar(session)
        assert len(events) == 1
        assert events[0].actor == 'SISTEMA'
        assert events[0].accion == 'Carga de los datos iniciales'
        session.commit.assert_awaited_once()
    asyncio.run(scenario())


def test_seed_trunca_14_tablas_y_carga_usuarios_y_roles(monkeypatch):
    async def scenario():
        orden_operaciones = []
        agregados = []
        hash_original = seed.hash_password

        async def espiar_hash(*args, **kwargs):
            orden_operaciones.append('hash_password')
            return await hash_original(*args, **kwargs)

        async def registrar_execute(stmt):
            orden_operaciones.append('execute')

        monkeypatch.setattr(seed, 'hash_password', espiar_hash)
        session = SimpleNamespace(
            execute=AsyncMock(side_effect=registrar_execute),
            add=Mock(side_effect=agregados.append),
            flush=AsyncMock(),
            commit=AsyncMock(),
        )
        await seed.cargar(session)

        sql_truncate = str(seed.VACIAR_TABLAS)
        for tabla in (
            'movimiento_stock', 'renglon_venta', 'venta', 'perfil_cliente',
            'cliente', 'libro_autor', 'libro', 'autor', 'genero', 'editorial',
            'asignacion_rol', 'usuario', 'intento_acceso', 'evento_seguridad',
        ):
            assert tabla in sql_truncate
        assert 'RESTART IDENTITY CASCADE' in sql_truncate

        # Regla dura 6: todos los hashes bcrypt se calculan antes de abrir transacción con execute()
        indice_execute = orden_operaciones.index('execute')
        assert indice_execute == 5
        assert orden_operaciones[:5] == ['hash_password'] * 5

        usuarios = [x for x in agregados if isinstance(x, Usuario)]
        assert [(u.email, u.activo, u.debe_cambiar_password) for u in usuarios] == [
            ('admin@example.com', True, False),
            ('admin2@example.com', True, False),
            ('vendedor@example.com', True, False),
            ('ana@example.com', True, False),
            ('nuevo@example.com', True, True),
        ]
        assert all(u.password_hash.startswith('$2b$') for u in usuarios)

        roles = [x for x in agregados if isinstance(x, AsignacionRol)]
        assert [(r.usuario_id, r.rol, r.vence_en, r.revocada_en) for r in roles] == [
            (1, 'ADMIN', None, None),
            (2, 'ADMIN', None, None),
            (3, 'VENDEDOR', None, None),
            (4, 'CLIENTE', None, None),
            (5, 'VENDEDOR', None, None),
        ]

    asyncio.run(scenario())


def test_seed_catalogo_clientes_venta_y_movimientos_stock():
    async def scenario():
        agregados = []
        session = SimpleNamespace(
            execute=AsyncMock(),
            add=Mock(side_effect=agregados.append),
            flush=AsyncMock(),
            commit=AsyncMock(),
        )
        await seed.cargar(session)

        editoriales = [x for x in agregados if isinstance(x, Editorial)]
        generos = [x for x in agregados if isinstance(x, Genero)]
        autores = [x for x in agregados if isinstance(x, Autor)]
        libros = [x for x in agregados if isinstance(x, Libro)]
        clientes = [x for x in agregados if isinstance(x, Cliente)]
        perfiles = [x for x in agregados if isinstance(x, PerfilCliente)]
        ventas = [x for x in agregados if isinstance(x, Venta)]
        movimientos = [x for x in agregados if isinstance(x, MovimientoStock)]

        assert len(editoriales) == 3
        assert len(generos) == 3
        assert len(autores) == 6
        assert [(l.titulo, l.isbn, l.precio, l.stock) for l in libros] == [
            ('Rayuela', '978-950-00-0001-1', Decimal('25000.00'), 10),
            ('Antología de la literatura fantástica', '978-950-00-0002-8', Decimal('30000.00'), 5),
            ('Ficciones', '978-950-00-0003-3', Decimal('22000.00'), 8),
            ('Respiración artificial', '978-950-00-0004-4', Decimal('27000.00'), 3),
            ('Bestiario', '978-950-00-0005-5', Decimal('19500.00'), 1),
        ]
        assert all(l.isbn != '978-950-00-0006-6' for l in libros)

        assert [(c.nombre, c.email, c.usuario_id) for c in clientes] == [
            ('Lucía Fernández', 'lucia@example.com', None),
            ('Tomás Ríos', 'tomas@example.com', None),
            ('Ana Paz', 'ana@example.com', 4),
        ]
        assert len(perfiles) == 1
        assert perfiles[0].cliente_id == 1

        assert len(ventas) == 1
        venta = ventas[0]
        assert venta.cliente_id == 1
        assert venta.total == Decimal('69000.00')
        assert [(r.libro_id, r.cantidad, r.precio_unitario) for r in venta.renglones] == [
            (1, 1, Decimal('25000.00')),
            (3, 2, Decimal('22000.00')),
        ]

        assert len(movimientos) == 7
        iniciales = [m for m in movimientos if m.motivo == 'Stock inicial']
        assert [(m.libro_id, m.venta_id, m.cantidad) for m in iniciales] == [
            (1, None, 11),
            (2, None, 5),
            (3, None, 10),
            (4, None, 3),
            (5, None, 1),
        ]
        salidas = [m for m in movimientos if m.venta_id == 1]
        assert [(m.libro_id, m.usuario_id, m.cantidad) for m in salidas] == [
            (1, 3, -1),
            (3, 3, -2),
        ]
        for idx, libro in enumerate(libros, start=1):
            suma = sum(m.cantidad for m in movimientos if m.libro_id == idx)
            assert suma == libro.stock

    asyncio.run(scenario())


