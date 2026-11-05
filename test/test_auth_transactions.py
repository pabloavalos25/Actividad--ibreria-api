import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.usuarios import service
from app.modules.usuarios.models import Usuario
from app.modules.ventas.models import Venta
from app.modules.libros.models import Libro
from app.modules.editoriales.models import Editorial
from app.modules.autores.models import Autor
from app.modules.generos.models import Genero
from app.modules.usuarios.schemas import Registro, CambiarPassword


@pytest.mark.parametrize('cambio',[False,True])
def test_hash_se_calcula_sin_transaccion_de_sesion(monkeypatch,cambio):
    async def scenario():
        active=cambio
        usuario=Usuario(id=7,email='ana@example.com',nombre='Ana',password_hash='hash')
        async def rollback():
            nonlocal active
            active=False
        repo=SimpleNamespace(add=AsyncMock(),por_email=AsyncMock(return_value=None),
            cliente_por_email=AsyncMock(return_value=None),por_id=AsyncMock(return_value=usuario))
        class Uow:
            session=SimpleNamespace(rollback=rollback)
            usuarios=repo
            terminar_lectura=staticmethod(rollback)
            async def __aenter__(self):
                nonlocal active
                active=True
                return self
            async def __aexit__(self,*args): pass
        async def hashed(*args,**kwargs):
            assert active is False, 'bcrypt hash con transacción abierta'
            return 'nuevo-hash'
        monkeypatch.setattr(service,'hash_password',hashed)
        monkeypatch.setattr(service,'verify_password',AsyncMock(return_value=True))
        settings=SimpleNamespace(bcrypt_rounds=4)
        if cambio:
            await service.cambiar_password(Uow(),usuario,CambiarPassword(password_actual='abcdefgh',password_nueva='nueva-clave'),settings,None)
        else:
            await service.registrar(Uow(),Registro(nombre='Ana',email='ana@example.com',password='abcdefgh'),settings,None)
    asyncio.run(scenario())
