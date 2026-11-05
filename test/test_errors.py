import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, DataError

from app.core.errors import conflicto_de_integridad


@pytest.mark.parametrize('exception,status',[(IntegrityError,409),(DataError,422)])
@pytest.mark.parametrize('internal',['SQL INSERT secreto','DB traceback password'])
def test_errores_bd_se_traducen_y_hacen_rollback(exception,status,internal):
    async def scenario():
        session=SimpleNamespace(rollback=AsyncMock())
        with pytest.raises(HTTPException) as caught:
            async with conflicto_de_integridad(session,'Conflicto con los datos guardados'):
                raise exception(internal,{},Exception(internal))
        assert caught.value.status_code == status
        assert internal not in str(caught.value.detail)
        session.rollback.assert_awaited_once()
    asyncio.run(scenario())
