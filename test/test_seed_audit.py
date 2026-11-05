import asyncio
from unittest.mock import AsyncMock, Mock
from types import SimpleNamespace

import pytest
import seed
from app.modules.usuarios.models import EventoSeguridad


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
