from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.core.database import get_session


@pytest.mark.parametrize('method,path', [
    ('POST','/editoriales/'), ('POST','/generos/'), ('POST','/autores/'),
    ('PATCH','/editoriales/1'), ('PATCH','/autores/1'), ('PATCH','/libros/1'),
    ('DELETE','/libros/1'), ('POST','/clientes/'), ('GET','/clientes/1'),
    ('PATCH','/clientes/1'), ('POST','/clientes/1/perfil'), ('GET','/clientes/1/ventas'),
    ('POST','/ventas/'), ('GET','/ventas/'), ('GET','/ventas/1'), ('GET','/mis-ventas'),
    ('POST','/usuarios'), ('GET','/usuarios/1/roles'), ('POST','/usuarios/1/roles'),
    ('DELETE','/usuarios/1/roles/ADMIN'), ('GET','/eventos'),
])
def test_rutas_privadas_sin_cookie_son_401(method,path):
    # Sin lifespan ni DB: sin cookie se rechaza antes de consultar datos.
    app.dependency_overrides[get_session] = lambda: None
    try:
        response = TestClient(app).request(method,path,json={} if method in ('POST','PATCH') else None)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401, response.text
