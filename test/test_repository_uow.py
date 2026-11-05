import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.core.unit_of_work import UnitOfWork
from app.modules.libros.models import Libro
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.repository import UsuarioRepository
from app.modules.ventas.models import Venta


@pytest.mark.parametrize('method', ['add', 'update'])
def test_repo_flush_sin_commit(method):
    async def run():
        session = SimpleNamespace(add=Mock(), flush=AsyncMock(), commit=AsyncMock())
        row = Libro(isbn='r', titulo='L', precio=1, editorial_id=1)
        assert await getattr(BaseRepository(session, Libro), method)(row) is row
        session.add.assert_called_once_with(row)
        session.flush.assert_awaited_once()
        session.commit.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('deleted', [False, True])
def test_soft_delete_filtra_y_permite_historia(deleted):
    async def run():
        session = SimpleNamespace(scalar=AsyncMock(return_value=None))
        repo = SoftDeleteRepository(session, Libro)
        method = repo.get_by_id_including_deleted if deleted else repo.get_by_id
        assert await method(9) is None
        sql = str(session.scalar.call_args.args[0].compile(dialect=postgresql.dialect()))
        assert ('borrado_en IS NULL' in sql) is (not deleted)
        assert not hasattr(BaseRepository, 'soft_delete')
    asyncio.run(run())


@pytest.mark.parametrize('failure', [None, 'body', 'commit'])
def test_uow_confirma_o_revierte_sin_cerrar(failure):
    async def run():
        session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock(), close=AsyncMock())
        if failure == 'commit': session.commit.side_effect = RuntimeError('commit')
        async def action():
            async with UnitOfWork(session):
                if failure == 'body': raise RuntimeError('body')
        if failure:
            with pytest.raises(RuntimeError): await action()
            session.rollback.assert_awaited_once()
        else:
            await action()
            session.commit.assert_awaited_once()
            session.rollback.assert_not_awaited()
        session.close.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('nombre', ['Ana', 'Beatriz'])
def test_repositorio_usuario_conserva_contrato_add(nombre):
    async def run():
        session = SimpleNamespace(add=Mock(), flush=AsyncMock(), commit=AsyncMock())
        usuario = Usuario(nombre=nombre, email='ana@example.test', password_hash='hash')
        assert await UsuarioRepository(session).add(usuario) is usuario
        session.add.assert_called_once_with(usuario)
        session.flush.assert_awaited_once()
        session.commit.assert_not_awaited()
    asyncio.run(run())
