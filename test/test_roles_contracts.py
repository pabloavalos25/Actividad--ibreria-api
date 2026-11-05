from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.modules.usuarios.schemas import PersonalCreate, RolCreate


@pytest.mark.parametrize('rol', ['ADMIN', 'VENDEDOR'])
def test_personal_provisional_admite_roles_de_personal(rol):
    data = PersonalCreate(nombre='Personal', email='p@example.com', password_provisoria='abcdefgh', rol=rol)
    assert data.rol == rol
    with pytest.raises(ValidationError):
        PersonalCreate(nombre='P', email='p@example.com', password_provisoria='x'*73, rol=rol)


@pytest.mark.parametrize('fecha', [datetime.now(), datetime.now(timezone.utc)-timedelta(days=1)])
def test_roles_rechazan_vencimiento_sin_zona_o_pasado(fecha):
    with pytest.raises(ValidationError):
        RolCreate(rol='ADMIN', vence_en=fecha)


@pytest.mark.parametrize('rol', ['ADMIN', 'CLIENTE', 'VENDEDOR'])
def test_roles_admiten_sin_vencimiento_o_fecha_futura(rol):
    assert RolCreate(rol=rol).vence_en is None
    fecha = datetime.now(timezone.utc)+timedelta(days=1)
    assert RolCreate(rol=rol, vence_en=fecha).vence_en == fecha


@pytest.mark.parametrize('data', [{'rol': 'OTRO'}, {'rol':'ADMIN','extra':1}])
def test_roles_estrictos(data):
    with pytest.raises(ValidationError):
        RolCreate(**data)
