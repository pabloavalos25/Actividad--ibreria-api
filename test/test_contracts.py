from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.autores.schemas import AutorCreate, AutorUpdate
from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate, PerfilCreate
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.generos.schemas import GeneroCreate, GeneroUpdate
from app.modules.libros.schemas import AutoriaCreate, LibroCreate, LibroUpdate
from app.modules.ventas.schemas import VentaCreate


@pytest.mark.parametrize('dto,payload', [
    (AutorCreate, dict(nombre='Ana', nacionalidad='AR')),
    (AutorUpdate, dict(nombre='Ana')),
    (ClienteCreate, dict(nombre='Ana', email='ana@example.test')),
    (ClienteUpdate, dict(nombre='Ana')),
    (PerfilCreate, dict(telefono='123')),
    (EditorialCreate, dict(nombre='E', pais='AR')),
    (EditorialUpdate, dict(nombre='E')),
    (GeneroCreate, dict(nombre='G')),
    (GeneroUpdate, dict(nombre='G')),
    (AutoriaCreate, dict(autor_id=1, rol='autor', orden=1)),
])
@pytest.mark.parametrize('extra', ['id', 'password_hash'])
def test_entradas_rechazan_campos_desconocidos(dto, payload, extra):
    with pytest.raises(ValidationError):
        dto.model_validate({**payload, extra: 'inyectado'})


@pytest.mark.parametrize('payload', [{'stock': 2}, {'isbn': 'nuevo'}, {'titulo': None}, {'precio': None}])
def test_patch_libro_solo_titulo_precio_y_no_null(payload):
    with pytest.raises(ValidationError):
        LibroUpdate.model_validate(payload)


@pytest.mark.parametrize('payload', [{'titulo': 'Nuevo'}, {'precio': '12.50'}, {}])
def test_patch_solo_aplica_campos_enviados(payload):
    dto = LibroUpdate.model_validate(payload)
    assert dto.model_dump(exclude_unset=True) == {
        k: Decimal(v) if k == 'precio' else v for k, v in payload.items()
    }


@pytest.mark.parametrize('field,value', [('titulo', 'x' * 201), ('isbn', 'x' * 21), ('precio', '1.001')])
def test_alta_limites_de_columnas(field, value):
    payload = dict(isbn='123', titulo='Libro', precio='10.00', stock_inicial=0, editorial_id=1)
    with pytest.raises(ValidationError):
        LibroCreate.model_validate({**payload, field: value})


@pytest.mark.parametrize('stock', [0, 5])
def test_alta_usa_stock_inicial(stock):
    payload = dict(isbn='123', titulo='Libro', precio='10.00', stock_inicial=stock, editorial_id=1)
    assert LibroCreate.model_validate(payload).stock_inicial == stock
    with pytest.raises(ValidationError):
        LibroCreate.model_validate({**payload, 'stock': stock})


@pytest.mark.parametrize('payload', [
    {'cliente_id': 1, 'renglones': []},
    {'cliente_id': 1, 'renglones': [{'libro_id': 1, 'cantidad': 1}] * 2},
    {'cliente_id': 1, 'renglones': [{'libro_id': 1, 'cantidad': 1, 'precio_unitario': 2}]},
    {'cliente_id': 1, 'renglones': [{'libro_id': 1, 'cantidad': 1}], 'total': 20},
])
def test_venta_no_admite_totales_precios_vacio_o_repetidos(payload):
    with pytest.raises(ValidationError):
        VentaCreate.model_validate(payload)


@pytest.mark.parametrize('dto,payload', [
    (AutorCreate, dict(nombre='x'*101, nacionalidad='AR')),
    (EditorialCreate, dict(nombre='x'*101, pais='AR')),
    (ClienteCreate, dict(nombre='Ana', email='x'*256)),
    (GeneroCreate, dict(nombre='x'*101)),
    (AutoriaCreate, dict(autor_id=1, rol='autor', orden=2**40)),
    (VentaCreate, dict(cliente_id=1, renglones=[dict(libro_id=1,cantidad=2**40)])),
])
def test_entradas_fuera_de_limites_bd_son_validacion(dto,payload):
    with pytest.raises(ValidationError):
        dto.model_validate(payload)
