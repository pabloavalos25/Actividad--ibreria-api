import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.modules.ventas.models import Venta
from app.modules.libros import service
from app.modules.libros.schemas import LibroCreate
from app.modules.libros.models import MovimientoStock
from test_crud_http import cliente, sesion_vacia


@pytest.mark.parametrize('stock', [0,3])
def test_alta_sin_sesion_autenticada_falla_cerrada(stock):
    with cliente(sesion_vacia()) as client:
        response=client.post('/libros/',json=dict(isbn='1',titulo='L',precio='2.50',stock_inicial=stock,editorial_id=1))
    assert response.status_code == 401


@pytest.mark.parametrize('stock', [0,3])
def test_alta_registra_movimiento_solo_si_stock_no_cero(monkeypatch,stock):
    async def scenario():
        session=SimpleNamespace(add=Mock(),commit=AsyncMock(),flush=AsyncMock(),rollback=AsyncMock())
        monkeypatch.setattr(service,'obtener_libro',AsyncMock(return_value='libro-creado'))
        datos=LibroCreate(isbn='1',titulo='L',precio='2.50',stock_inicial=stock,editorial_id=1)
        assert await service.crear_libro(session,datos,usuario_id=7) == 'libro-creado'
        libro=session.add.call_args_list[0].args[0]
        assert libro.stock == stock
        movimientos=[c.args[0] for c in session.add.call_args_list if isinstance(c.args[0],MovimientoStock)]
        assert len(movimientos) == (1 if stock else 0)
        if stock:
            assert movimientos[0].usuario_id == 7
            assert movimientos[0].cantidad == stock
            assert movimientos[0].motivo == 'Stock inicial'
            assert movimientos[0].libro is libro
        session.commit.assert_awaited_once()
    asyncio.run(scenario())


@pytest.mark.parametrize('missing',[False,True])
def test_baja_logica_204_o_404(monkeypatch,missing):
    libro=SimpleNamespace(borrado_en=None)
    obtener=AsyncMock(return_value=libro)
    if missing:
        obtener.side_effect=HTTPException(404,'Libro no encontrado')
    monkeypatch.setattr(service,'obtener_libro',obtener)
    session=sesion_vacia()
    session.commit=AsyncMock()
    with cliente(session) as client:
        response=client.delete('/libros/1')
    assert response.status_code == (404 if missing else 204)
    if not missing:
        assert response.content == b''
        assert libro.borrado_en.utcoffset() is not None
        session.commit.assert_awaited_once()
