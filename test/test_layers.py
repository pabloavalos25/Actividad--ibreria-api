import ast
import inspect
from importlib import import_module
from pathlib import Path

import pytest

from app.core.repository import BaseRepository
from app.core.unit_of_work import UnitOfWork


@pytest.mark.parametrize('module,repo,uow', [
    ('autores','AutorRepository','AutoresUnitOfWork'),
    ('editoriales','EditorialRepository','EditorialesUnitOfWork'),
    ('generos','GeneroRepository','GenerosUnitOfWork'),
    ('clientes','ClienteRepository','ClientesUnitOfWork'),
    ('usuarios','UsuarioRepository','UsuariosUnitOfWork'),
    ('libros','LibroRepository','LibrosUnitOfWork'),
    ('ventas','VentaRepository','VentasUnitOfWork'),
])
def test_repositorio_y_uow_por_modulo(module,repo,uow):
    repository = getattr(import_module(f'app.modules.{module}.repository'),repo)
    unit = getattr(import_module(f'app.modules.{module}.unit_of_work'),uow)
    assert issubclass(repository,BaseRepository)
    assert issubclass(unit,UnitOfWork)


@pytest.mark.parametrize('module',['autores','editoriales','generos','clientes','usuarios','libros','ventas'])
def test_servicios_sin_sql_ni_sesion(module):
    tree=ast.parse(Path(f'app/modules/{module}/service.py').read_text(encoding='utf-8-sig'))
    forbidden=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('sqlalchemy'):
            forbidden.append(node.module)
        if isinstance(node,ast.Attribute) and node.attr=='session':
            forbidden.append('session')
        if isinstance(node,ast.AsyncFunctionDef):
            assert 'session' not in [arg.arg for arg in node.args.args]
    assert not forbidden, forbidden
