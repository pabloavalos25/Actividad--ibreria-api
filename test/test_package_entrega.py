"""Tests for the final delivery ZIP packaging script and root main.py entrypoint (CH-15)."""

from pathlib import Path
import zipfile

import pytest


def test_root_main_exports_fastapi_app_and_factory() -> None:
    """Verify root main.py re-exports app and lifespan from app.main and provides create_app."""
    import main
    from app.main import app as app_instance, lifespan as lifespan_cm

    assert main.app is app_instance
    assert main.lifespan is lifespan_cm
    assert main.create_app() is app_instance


def test_build_and_verify_entrega_zip_structure_and_exclusions(tmp_path: Path) -> None:
    """Verify build_entrega_zip produces a compliant ZIP with parcial/ and despliegue/."""
    from scripts.package_entrega import build_entrega_zip, verify_entrega_zip

    out_zip = tmp_path / "Parcial_Cap1a6_Avalos_Blangetti_Suarez.zip"
    result_path = build_entrega_zip(output_path=out_zip)

    assert result_path == out_zip
    assert out_zip.is_file()

    summary = verify_entrega_zip(out_zip)
    assert summary["root_dirs"] == ["despliegue", "parcial"]
    assert summary["total_files"] > 40

    with zipfile.ZipFile(out_zip, "r") as zf:
        names = set(zf.namelist())

    top_levels = {name.split("/", 1)[0] for name in names if name}
    assert top_levels == {"parcial", "despliegue"}

    expected_entries = {
        "parcial/main.py",
        "parcial/app/main.py",
        "parcial/seed.py",
        "parcial/alembic.ini",
        "parcial/env.example",
        "parcial/requirements.txt",
        "parcial/README.md",
        "parcial/migrations/versions/846f445b2248_esquema_inicial_sin_genero.py",
        "parcial/migrations/versions/332ba12e013b_agrega_genero_y_libro_genero_id.py",
        "parcial/migrations/versions/3e5d56535b0e_acceso_y_movimientos_stock.py",
        "parcial/migrations/versions/a05a50bc58a8_movimiento_stock_solo_agregado.py",
        "parcial/test/casos_acceso_autorizacion.http",
        "parcial/test/casos_ventas_stock_catalogo.http",
        "parcial/test/solo_agregado.sql",
        "parcial/evidencia/c14_psql.txt",
        "parcial/evidencia/c15_consultas.txt",
        "despliegue/Dockerfile",
        "despliegue/.dockerignore",
        "despliegue/docker-entrypoint.sh",
        "despliegue/healthcheck.py",
        "despliegue/env.example",
        "despliegue/DEPLOY.md",
        "despliegue/README.md",
        "despliegue/seed.py",
        "despliegue/alembic.ini",
        "despliegue/requirements.txt",
        "despliegue/migrations/versions/846f445b2248_esquema_inicial_sin_genero.py",
        "despliegue/migrations/versions/332ba12e013b_agrega_genero_y_libro_genero_id.py",
        "despliegue/evidencia/docker_local.txt",
        "despliegue/evidencia/ejercicio10_simulacion_local.md",
        "despliegue/evidencia/vps_local_simulation.txt",
        "despliegue/evidencia/vps_ejercicio10.md",
        "despliegue/evidencia/vps_transcript.txt",
    }
    missing = expected_entries - names
    assert not missing, f"Missing expected entries in ZIP: {sorted(missing)}"

    forbidden_segments = {
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "tmp",
        ".git",
        "openspec",
        "knowledge-base",
        ".atl",
        ".claude",
        ".codegraph",
    }
    for entry in names:
        parts = Path(entry).parts
        assert not (set(parts) & forbidden_segments), f"Forbidden segment in {entry}"
        filename = parts[-1]
        assert filename != ".env" and not filename.startswith(".env."), f"Secret env file in {entry}"
        assert not filename.endswith((".pyc", ".pyo", ".zip")), f"Forbidden extension in {entry}"


@pytest.mark.parametrize(
    "missing_entry",
    [
        "despliegue/evidencia/vps_ejercicio10.md",
        "despliegue/evidencia/vps_transcript.txt",
    ],
)
def test_verify_entrega_zip_requires_real_vps_evidence(
    tmp_path: Path, missing_entry: str
) -> None:
    """Reject archives missing either real VPS evidence file, even with local evidence."""
    from scripts.package_entrega import REQUIRED_ZIP_ENTRIES, verify_entrega_zip

    entries = set(REQUIRED_ZIP_ENTRIES) | {
        "despliegue/evidencia/vps_ejercicio10.md",
        "despliegue/evidencia/vps_transcript.txt",
    }
    incomplete_zip = tmp_path / "missing_vps_evidence.zip"
    with zipfile.ZipFile(incomplete_zip, "w") as zf:
        for entry in sorted(entries - {missing_entry}):
            zf.writestr(entry, "test fixture\n")

    with pytest.raises(ValueError, match=missing_entry):
        verify_entrega_zip(incomplete_zip)


def test_verify_entrega_zip_rejects_forbidden_or_incomplete_archive(tmp_path: Path) -> None:
    """Verify verify_entrega_zip raises ValueError when forbidden files or missing dirs exist."""
    from scripts.package_entrega import verify_entrega_zip

    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("parcial/.env", "POSTGRES_PASSWORD=secret")
        zf.writestr("despliegue/Dockerfile", "FROM python:3.12-alpine\n")

    with pytest.raises(ValueError, match="prohibid|obligatori"):
        verify_entrega_zip(bad_zip)
