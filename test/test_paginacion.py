import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.paginacion import paginar
from app.modules.libros.models import Libro
from app.modules.ventas.models import Venta
from app.modules.usuarios.models import Usuario


@pytest.mark.parametrize('total,page,size,expected_pages', [(0,1,20,1),(21,2,20,2),(4,2,2,2)])
def test_pagina_total_filtros_y_limites(total,page,size,expected_pages):
    async def scenario():
        items = [SimpleNamespace(id=5)] if total else []
        result = SimpleNamespace(scalars=lambda: SimpleNamespace(unique=lambda: SimpleNamespace(all=lambda:items)))
        session = SimpleNamespace(scalar=AsyncMock(return_value=total), execute=AsyncMock(return_value=result))
        query = select(Libro).where(Libro.titulo.ilike('%Ana%')).order_by(Libro.id)
        actual = await paginar(session, query, page, size)
        assert actual == dict(items=items,total=total,page=page,size=size,pages=expected_pages)
        count = str(session.scalar.call_args.args[0])
        listing = session.execute.call_args.args[0]
        assert 'lower(libro.titulo)' in count
        assert listing._offset_clause.value == (page-1)*size
        assert listing._limit_clause.value == size
        assert listing.compile().params['titulo_1'] == '%Ana%'
    asyncio.run(scenario())


@pytest.mark.parametrize('total,page,size', [(0,2,20),(3,3,2),(5,0,20),(5,1,101),(5,1,0)])
def test_pagina_invalida_da_422_sin_ejecutar_listado(total,page,size):
    async def scenario():
        session=SimpleNamespace(scalar=AsyncMock(return_value=total),execute=AsyncMock())
        with pytest.raises(HTTPException) as caught:
            await paginar(session,select(Libro),page,size)
        assert caught.value.status_code == 422
        session.execute.assert_not_called()
    asyncio.run(scenario())
