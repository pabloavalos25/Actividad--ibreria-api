from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_README = RAIZ / "README.md"
RUTA_ENV_EXAMPLE = RAIZ / "env.example"


def test_readme_integrantes_variables_y_puesta_en_marcha():
    assert RUTA_README.exists(), "Falta README.md en la raíz"
    contenido = RUTA_README.read_text(encoding="utf-8")

    for integrante in ("Pablo Avalos", "Ismael Suarez", "Sofia Blangetti"):
        assert integrante in contenido, f"Falta integrante {integrante} en README.md"

    assert "parcial/" in contenido
    assert "despliegue/" in contenido

    # Todas las variables de env.example deben estar documentadas en README.md
    for linea in RUTA_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            variable = linea.split("=", 1)[0].strip()
            assert variable in contenido, f"Falta documentar variable {variable} en README.md"

    # Comandos obligatorios de puesta en marcha
    assert "secrets.token_urlsafe(48)" in contenido
    assert "alembic upgrade head" in contenido
    assert "seed.py" in contenido
    assert "uvicorn app.main:app --reload" in contenido

    # Cuentas iniciales de seed.py
    for cuenta in (
        "admin@example.com",
        "admin2@example.com",
        "vendedor@example.com",
        "ana@example.com",
        "nuevo@example.com",
        "secreto123",
    ):
        assert cuenta in contenido, f"Falta cuenta/clave inicial {cuenta} en README.md"


def test_readme_casos_c01_a_c16_y_sin_afirmaciones_obsoletas():
    contenido = RUTA_README.read_text(encoding="utf-8")

    for num in range(1, 17):
        caso = f"C-{num:02d}"
        assert caso in contenido, f"Falta referencia al caso {caso} en README.md"

    for archivo in (
        "test/casos_acceso_autorizacion.http",
        "test/casos_ventas_stock_catalogo.http",
        "test/solo_agregado.sql",
        "evidencia/ej7_integridad.md",
        "evidencia/c14_psql.txt",
        "evidencia/ej8_lecturas.md",
        "evidencia/ej8_comprobante.md",
    ):
        assert archivo in contenido, f"Falta referencia a {archivo} en README.md"

    for frase_obsoleta in (
        "El parcial está en desarrollo",
        "aún no prepara los usuarios/roles",
        "requerir_usuario_id",
        "test/evidencia_c07.md",
    ):
        assert frase_obsoleta not in contenido, f"Frase obsoleta en README.md: {frase_obsoleta}"


def test_readme_repositorio_visible_al_inicio():
    contenido = RUTA_README.read_text(encoding="utf-8")
    inicio = "\n".join(contenido.splitlines()[:15])

    assert "https://github.com/pabloavalos25/Actividad--ibreria-api" in inicio, (
        "Falta URL del repositorio en las primeras 15 líneas de README.md"
    )


def test_readme_despliegue_en_linea_y_evidencia():
    contenido = RUTA_README.read_text(encoding="utf-8")

    for referencia in (
        "https://api.ismaelsuarez.me",
        "https://api.ismaelsuarez.me/docs",
        "despliegue/DEPLOY.md",
        "despliegue/evidencia/vps_ejercicio10.md",
    ):
        assert referencia in contenido, f"Falta referencia a {referencia} en README.md"


def test_readme_seccion_integrantes_con_insignias():
    contenido = RUTA_README.read_text(encoding="utf-8")

    assert any(
        linea.startswith("## ") and "Integrantes" in linea
        for linea in contenido.splitlines()
    ), "Falta sección Integrantes en README.md"
    assert "https://img.shields.io/badge/" in contenido, "Faltan insignias en README.md"


def test_readme_sin_datos_incorrectos_del_dominio():
    contenido = RUTA_README.read_text(encoding="utf-8")

    for dato_incorrecto in (
        "eliminado_en",
        "Mariana Enríquez",
        "prologuista",
        '"status": "ok"',
        "Ficción",
        "Ensayo",
    ):
        assert dato_incorrecto not in contenido, f"Dato incorrecto en README.md: {dato_incorrecto}"
