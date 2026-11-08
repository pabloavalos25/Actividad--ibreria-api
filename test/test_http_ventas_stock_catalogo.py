import json
import re
from pathlib import Path

DIR_TEST = Path(__file__).resolve().parent
RUTA_HTTP = DIR_TEST / "casos_ventas_stock_catalogo.http"


def test_http_ventas_stock_c10_a_c12_estructura():
    assert RUTA_HTTP.exists(), "Falta test/casos_ventas_stock_catalogo.http"
    contenido = RUTA_HTTP.read_text(encoding="utf-8")

    assert "python seed.py" in contenido
    assert "@base = http://127.0.0.1:8000" in contenido
    assert "@password = secreto123" in contenido
    assert "# @name login_vendedor" in contenido
    assert "# @name login_admin" in contenido
    assert "# @no-cookie-jar" in contenido

    for caso in ("### C-10", "### C-11", "### C-12"):
        assert caso in contenido, f"Falta sección {caso}"

    # C-10: venta válida con 2 renglones, descuento de stock y movimientos
    assert "POST {{base}}/ventas/" in contenido
    assert '"57000.00"' in contenido
    assert "GET {{base}}/libros/2/movimientos" in contenido
    assert "GET {{base}}/libros/4/movimientos" in contenido
    assert "Comprobante de venta" in contenido

    # C-11: rechazo todo-o-nada por falta de stock (Rayuela sigue en 10, Bestiario en 1)
    assert "Libro no disponible o stock insuficiente" in contenido
    assert "GET {{base}}/libros/1" in contenido
    assert "GET {{base}}/libros/5" in contenido

    # C-12: cliente inexistente, libro inexistente y libro dado de baja -> 409
    assert '"cliente_id": 999' in contenido
    assert '"libro_id": 999' in contenido
    assert "Cliente inexistente" in contenido


def test_http_catalogo_c13_a_c16_estructura():
    contenido = RUTA_HTTP.read_text(encoding="utf-8")

    for caso in ("### C-13", "### C-14", "### C-15", "### C-16"):
        assert caso in contenido, f"Falta sección {caso}"

    # C-13: reposición, baja lógica de Ficciones (id=3), ISBN parcial e historial en venta 1
    assert "POST {{base}}/libros/5/reponer" in contenido
    assert "DELETE {{base}}/libros/3" in contenido
    assert "GET {{base}}/libros/?titulo=Ficciones" in contenido
    assert "POST {{base}}/libros/3/reponer" in contenido
    assert '"978-950-00-0003-3"' in contenido
    assert "GET {{base}}/ventas/1" in contenido

    # C-14: referencia a test/solo_agregado.sql y evidencia/ej7_integridad.md
    assert "test/solo_agregado.sql" in contenido
    assert "evidencia/ej7_integridad.md" in contenido

    # C-15: lectura sin N+1 (2 renglones y 4 renglones) vinculada a evidencia/ej8_lecturas.md
    assert "evidencia/ej8_lecturas.md" in contenido
    assert "GET {{base}}/ventas/3" in contenido

    # C-16: búsqueda segura, paginación y actualización parcial sin stock
    assert "GET {{base}}/libros/?titulo=%27%20OR%20%271%27%3D%271" in contenido
    assert "GET {{base}}/libros/?titulo=ficc&size=1" in contenido
    assert "GET {{base}}/libros/?titulo=ficc&size=1&page=2" in contenido
    assert "GET {{base}}/libros/?size=500" in contenido
    assert "PATCH {{base}}/libros/1" in contenido
    assert '"26500.00"' in contenido
    assert '"stock": 99' in contenido

    # Verificar que los archivos heredados del TP 1-4 ya no estén en test/ de la raíz
    for heredado in ("casos_errores.http", "casos_venta.http", "evidencia_c07.md"):
        assert not (DIR_TEST / heredado).exists(), f"Debe retirarse test/{heredado}"

    # Verificar que todos los bloques con cuerpo JSON tengan JSON válido sin comentarios posteriores
    for bloque in re.split(r"^###.*$", contenido, flags=re.M)[1:]:
        lineas = bloque.strip().splitlines()
        if any(l.strip().startswith("Content-Type: application/json") for l in lineas):
            idx_vacio = next(i for i, l in enumerate(lineas) if l.strip() == "")
            cuerpo = "\n".join(lineas[idx_vacio + 1 :]).replace("{{password}}", "secreto123")
            json.loads(cuerpo)
