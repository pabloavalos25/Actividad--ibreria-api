import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from app.modules.usuarios.service import revocar_rol


@pytest.mark.parametrize('remaining', [0, 1])
def test_revocacion_no_deja_cero_administradores(remaining):
    class Uow:
        def __init__(self):
            self.usuarios=SimpleNamespace(
                por_id=AsyncMock(return_value=SimpleNamespace(id=1,email='admin@example.com',activo=True,debe_cambiar_password=False)),
                roles_vigentes=AsyncMock(return_value=['ADMIN']),
                rol_abierto=AsyncMock(return_value=SimpleNamespace(revocada_en=None)),
                cantidad_admin=AsyncMock(return_value=remaining), add=AsyncMock())
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
    async def scenario():
        uow=Uow()
        if remaining:
            assert await revocar_rol(uow,1,2,'ADMIN') == {'mensaje':'Rol revocado'}
            assert uow.usuarios.add.await_count==2
        else:
            with pytest.raises(HTTPException) as error:
                await revocar_rol(uow,1,2,'ADMIN')
            assert error.value.status_code==409
            uow.usuarios.add.assert_not_awaited()
    asyncio.run(scenario())
