import json
import re
from pathlib import Path

RUTA_HTTP = Path(__file__).resolve().parent / "casos_acceso_autorizacion.http"


def test_http_acceso_c01_a_c05_estructura():
    assert RUTA_HTTP.exists(), "Falta test/casos_acceso_autorizacion.http"
    contenido = RUTA_HTTP.read_text(encoding="utf-8")

    assert "python seed.py" in contenido
    assert "@base = http://127.0.0.1:8000" in contenido
    assert "@password = secreto123" in contenido
    assert "# @name " in contenido
    assert "# @no-cookie-jar" in contenido

    for caso in ("### C-01", "### C-02", "### C-03", "### C-04", "### C-05"):
        assert caso in contenido, f"Falta sección {caso}"

    # C-01: parámetro no entero con sesión iniciada -> 422
    assert "GET {{base}}/libros/abc" in contenido
    # C-02: registro válido 201 y colisiones con ana@example.com y lucia@example.com -> 409
    assert "POST {{base}}/auth/registro" in contenido
    assert '"ana@example.com"' in contenido
    assert '"lucia@example.com"' in contenido
    # C-03: cookie HttpOnly y rechazo de Authorization: Bearer -> 401
    assert "Authorization: Bearer" in contenido
    assert "HttpOnly" in contenido
    # C-04: correo existente vs inexistente -> 401 Credenciales inválidas
    assert "Credenciales inválidas" in contenido
    # C-05: 6 intentos fallidos -> 429 con Retry-After
    assert "429" in contenido
    assert "Retry-After" in contenido


def test_http_autorizacion_c06_a_c09_estructura():
    contenido = RUTA_HTTP.read_text(encoding="utf-8")

    for caso in ("### C-06", "### C-07", "### C-08", "### C-09"):
        assert caso in contenido, f"Falta sección {caso}"

    # C-06: sin sesión 401, vendedor creando libro 403, cliente ve su venta 200 y no la ajena 403
    assert "POST {{base}}/ventas/" in contenido
    assert "POST {{base}}/libros/" in contenido
    assert "GET {{base}}/ventas/1" in contenido
    assert "GET {{base}}/mis-ventas" in contenido

    # C-07: revocación con sesión abierta, /auth/yo con roles_vigentes vs roles_token, historial y 422 en vence_en
    assert "DELETE {{base}}/usuarios/3/roles/VENDEDOR" in contenido
    assert "roles_vigentes" in contenido
    assert "roles_token" in contenido
    assert "GET {{base}}/usuarios/3/roles" in contenido
    assert "POST {{base}}/usuarios/3/roles" in contenido

    # C-08: autoprotección de ADMIN -> 409
    assert "DELETE {{base}}/usuarios/1/roles/ADMIN" in contenido
    assert "No puede revocar su propio ADMIN" in contenido

    # C-09: nuevo@example.com cambio obligatorio -> 403 fuera de /auth y 200 tras POST /auth/cambiar-password
    assert '"nuevo@example.com"' in contenido
    assert "POST {{base}}/auth/cambiar-password" in contenido

    # Verificar que todos los bloques con cuerpo JSON tengan JSON válido sin comentarios posteriores
    for bloque in re.split(r"^###.*$", contenido, flags=re.M)[1:]:
        lineas = bloque.strip().splitlines()
        if any(l.strip().startswith("Content-Type: application/json") for l in lineas):
            idx_vacio = next(i for i, l in enumerate(lineas) if l.strip() == "")
            cuerpo = "\n".join(lineas[idx_vacio + 1 :]).replace("{{password}}", "secreto123")
            json.loads(cuerpo)


