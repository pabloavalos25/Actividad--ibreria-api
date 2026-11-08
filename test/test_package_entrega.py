"""Tests for the final delivery ZIP packaging script and root main.py entrypoint (CH-15)."""

from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
REQUIRES_REPO_LAYOUT = pytest.mark.skipif(
    not (ROOT / "despliegue").is_dir(),
    reason="Requiere el checkout del repositorio con despliegue/; no aplica a la entrega extraída parcial/",
)


@pytest.fixture
def entrega_repo(tmp_path: Path) -> Path:
    """Create the required delivery layout without relying on the checkout."""
    from scripts.package_entrega import REQUIRED_ZIP_ENTRIES

    repo = tmp_path / "repo"
    for entry in REQUIRED_ZIP_ENTRIES:
        relative = entry.removeprefix("parcial/")
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test fixture\n", encoding="utf-8")
    return repo


def test_build_entrega_zip_rewrites_only_parcial_links_to_despliegue(
    tmp_path: Path, entrega_repo: Path
) -> None:
    """Adapt cross-project links to sibling ZIP roots without editing sources."""
    from scripts.package_entrega import build_entrega_zip

    readme = (
        "[Deploy](despliegue/DEPLOY.md#inicio)\n"
        "![Evidence](./despliegue/evidencia/vps_ejercicio10.md)\n"
        '[Encoded](despliegue/file%20one.md#section "Title")\n'
        "[Directory](despliegue/)\n"
        "[Local](docs/A.md) [Web](https://example.org/missing)\n"
        "[Mail](mailto:example@example.org) [Anchor](#inicio)\n"
    )
    (entrega_repo / "README.md").write_text(readme, encoding="utf-8")
    docs = entrega_repo / "docs"
    docs.mkdir()
    (docs / "A.md").write_text(
        "[Deploy](../despliegue/DEPLOY.md#inicio)\n", encoding="utf-8"
    )
    (entrega_repo / "despliegue/file one.md").write_text("Evidence\n", encoding="utf-8")
    deploy = "[Evidence](evidencia/vps_ejercicio10.md#inicio)\n"
    (entrega_repo / "despliegue/DEPLOY.md").write_text(deploy, encoding="utf-8")

    out_zip = build_entrega_zip(tmp_path / "delivery.zip", repo_root=entrega_repo)

    with zipfile.ZipFile(out_zip) as zf:
        assert zf.read("parcial/README.md").decode() == (
            "[Deploy](../despliegue/DEPLOY.md#inicio)\n"
            "![Evidence](../despliegue/evidencia/vps_ejercicio10.md)\n"
            '[Encoded](../despliegue/file%20one.md#section "Title")\n'
            "[Directory](../despliegue)\n"
            "[Local](docs/A.md) [Web](https://example.org/missing)\n"
            "[Mail](mailto:example@example.org) [Anchor](#inicio)\n"
        )
        assert zf.read("parcial/docs/A.md").decode() == (
            "[Deploy](../../despliegue/DEPLOY.md#inicio)\n"
        )
        assert zf.read("despliegue/DEPLOY.md").decode() == deploy
    assert (entrega_repo / "README.md").read_text(encoding="utf-8") == readme
    assert (docs / "A.md").read_text(encoding="utf-8") == (
        "[Deploy](../despliegue/DEPLOY.md#inicio)\n"
    )


@pytest.mark.parametrize(
    ("entry", "link", "target"),
    [
        ("parcial/README.md", "[Missing](missing.md#section)", "missing.md#section"),
        ("parcial/docs/A.md", "![Missing](../missing.png)", "../missing.png"),
        ("despliegue/DEPLOY.md", "[Missing](missing/)", "missing/"),
        (
            "despliegue/evidencia/vps_ejercicio10.md",
            '[Missing](missing%20file.md#section "Title")',
            "missing%20file.md#section",
        ),
    ],
)
def test_verify_entrega_zip_rejects_broken_relative_markdown_links(
    tmp_path: Path, entry: str, link: str, target: str
) -> None:
    """Every packaged Markdown file must name a present file or directory."""
    from scripts.package_entrega import REQUIRED_ZIP_ENTRIES, verify_entrega_zip

    out_zip = tmp_path / "broken_link.zip"
    with zipfile.ZipFile(out_zip, "w") as zf:
        for name in sorted(set(REQUIRED_ZIP_ENTRIES) | {entry}):
            zf.writestr(name, link if name == entry else "test fixture\n")

    with pytest.raises(ValueError) as exc:
        verify_entrega_zip(out_zip)
    assert entry in str(exc.value)
    assert target in str(exc.value)


def test_verify_entrega_zip_accepts_existing_relative_targets_and_ignores_urls(
    tmp_path: Path,
) -> None:
    """Resolve anchors, URL-encoded files, and explicit or implicit directories."""
    from scripts.package_entrega import REQUIRED_ZIP_ENTRIES, verify_entrega_zip

    out_zip = tmp_path / "valid_links.zip"
    with zipfile.ZipFile(out_zip, "w") as zf:
        for name in REQUIRED_ZIP_ENTRIES:
            text = "test fixture\n"
            if name == "parcial/README.md":
                text = (
                    "[Sibling](../despliegue/DEPLOY.md#inicio)\n"
                    "![Encoded](docs/image%20one.png#preview)\n"
                    '[Angle](<docs/image one.png> "Title")\n'
                    "[Parentheses](docs/image(2).png)\n"
                    "[Implicit directory](../despliegue/)\n"
                    "[Explicit directory](empty/)\n"
                    "[Self](#anchor)\n"
                    "[Web](http://example.org/missing)\n"
                    "[Secure](https://example.org/missing)\n"
                    "[Mail](mailto:example@example.org)\n"
                )
            zf.writestr(name, text)
        zf.writestr("parcial/docs/image one.png", b"image")
        zf.writestr("parcial/docs/image(2).png", b"image")
        zf.writestr("parcial/empty/", b"")

    summary = verify_entrega_zip(out_zip)
    assert summary["root_dirs"] == ["despliegue", "parcial"]


def test_root_main_exports_fastapi_app_and_factory() -> None:
    """Verify root main.py re-exports app and lifespan from app.main and provides create_app."""
    import main
    from app.main import app as app_instance, lifespan as lifespan_cm

    assert main.app is app_instance
    assert main.lifespan is lifespan_cm
    assert main.create_app() is app_instance


@REQUIRES_REPO_LAYOUT
def test_build_and_verify_entrega_zip_structure_and_exclusions(tmp_path: Path) -> None:
    """Build the real repository and verify its structure, exclusions, and links."""
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
    assert not missing, f"Faltan entradas esperadas en el ZIP: {sorted(missing)}"

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
        assert not (set(parts) & forbidden_segments), f"Segmento prohibido en {entry}"
        filename = parts[-1]
        assert filename != ".env" and not filename.startswith(".env."), f"Archivo de entorno con secretos en {entry}"
        assert not filename.endswith((".pyc", ".pyo", ".zip")), f"Extensión prohibida en {entry}"


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
