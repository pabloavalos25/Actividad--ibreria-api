from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from importlib import import_module
from app.modules.usuarios.models import Usuario
from app.core.database import get_session

LISTADOS = ['/libros/', '/editoriales/', '/generos/', '/ventas/',
            '/autores/1/libros', '/clientes/1/ventas',
            '/editoriales/1/libros', '/generos/1/libros']


def cliente(session):
    app = FastAPI()
    for module in ["autores", "clientes", "editoriales", "generos", "libros", "ventas"]:
        app.include_router(import_module(f"app.modules.{module}.router").router)
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def sesion_vacia():
    result = SimpleNamespace(
        scalar_one_or_none=lambda: SimpleNamespace(id=1),
        scalars=lambda: SimpleNamespace(unique=lambda: SimpleNamespace(all=lambda: []), all=lambda: []),
    )
    return SimpleNamespace(scalar=AsyncMock(return_value=0), execute=AsyncMock(return_value=result))


@pytest.mark.parametrize('ruta', LISTADOS)
def test_listados_envuelven_resultado_vacio(ruta):
    with cliente(sesion_vacia()) as client:
        response = client.get(ruta)
    assert response.status_code == 200
    assert response.json() == dict(items=[], total=0, page=1, size=20, pages=1)


@pytest.mark.parametrize('ruta', LISTADOS)
@pytest.mark.parametrize('query', ['page=0','size=101','size=0','page=2'])
def test_listados_parametros_invalidos_son_422(ruta,query):
    with cliente(sesion_vacia()) as client:
        response = client.get(f'{ruta}?{query}')
    assert response.status_code == 422


@pytest.mark.parametrize('path,payload', [
    ('autores', {'nombre': None}), ('editoriales', {'pais': None}),
    ('clientes', {'email': None}), ('libros', {'titulo': None}),
])
def test_patch_null_no_nullable_es_422(path,payload):
    with cliente(sesion_vacia()) as client:
        response=client.patch(f'/{path}/1',json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize('path',['/libros/','/autores/','/clientes/','/editoriales/','/ventas/'])
@pytest.mark.parametrize('invalid',['0',str(2**40)])
def test_ids_fuera_de_rango_son_422(path,invalid):
    with cliente(sesion_vacia()) as client:
        response=client.get(path+invalid)
    assert response.status_code == 422
