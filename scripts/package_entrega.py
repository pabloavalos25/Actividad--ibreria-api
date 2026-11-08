"""Empaquetador reproducible de la entrega final Parcial Capítulos 1 a 6 (CH-15).

Construye el archivo ``Parcial_Cap1a6_<NombreDelGrupo>.zip`` con las dos carpetas
raíz exigidas por la consigna (``docs/Parcial_Cap1a6_Consigna.pdf``, página 24):
- ``parcial/``: código fuente, migraciones, ``seed.py``, casos ``.http``,
  ``solo_agregado.sql``, suite ``pytest``, ``README.md`` y ``evidencia/``.
- ``despliegue/``: proyecto del TP 1–4 preservado con ``Dockerfile``,
  ``.dockerignore``, ``docker-entrypoint.sh``, ``healthcheck.py``, ``DEPLOY.md``
  y ``evidencia/`` (``D-01`` a ``D-08``).

Excluye estrictamente ``.venv/``, ``__pycache__/``, ``*.pyc``, ``.pytest_cache/``,
``tmp/``, ``.env``, ``.git/``, archivos ``.zip`` y artefactos de agentes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import posixpath
import re
from typing import Any
from urllib.parse import quote, unquote, urlsplit
import zipfile

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GROUP_NAME = "Avalos_Blangetti_Suarez"

# Rutas de primer nivel del repositorio raíz que se empaquetan bajo parcial/
PARCIAL_ALLOWED_ROOT_ITEMS: tuple[str, ...] = (
    "app",
    "main.py",
    "seed.py",
    "alembic.ini",
    "env.example",
    "requirements.txt",
    "requirements-dev.txt",
    "pytest.ini",
    "README.md",
    "migrations",
    "test",
    "postgres_tests",
    "scripts",
    "docs",
    "evidencia",
    ".gitignore",
)

FORBIDDEN_DIR_NAMES: frozenset[str] = frozenset(
    {
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
)

FORBIDDEN_FILE_NAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".active-orchestrator-state.json",
        "CHANGES.md",
        "AGENTS.md",
        "CLAUDE.md",
        "engram-export.json",
    }
)

FORBIDDEN_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo", ".zip")

REQUIRED_ZIP_ENTRIES: tuple[str, ...] = (
    "parcial/main.py",
    "parcial/app/main.py",
    "parcial/seed.py",
    "parcial/alembic.ini",
    "parcial/env.example",
    "parcial/requirements.txt",
    "parcial/README.md",
    "parcial/migrations/env.py",
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
    "despliegue/migrations/env.py",
    "despliegue/migrations/versions/846f445b2248_esquema_inicial_sin_genero.py",
    "despliegue/migrations/versions/332ba12e013b_agrega_genero_y_libro_genero_id.py",
    "despliegue/evidencia/docker_local.txt",
    "despliegue/evidencia/ejercicio10_simulacion_local.md",
    "despliegue/evidencia/vps_local_simulation.txt",
    "despliegue/evidencia/vps_ejercicio10.md",
    "despliegue/evidencia/vps_transcript.txt",
)


def _is_excluded(rel_parts: tuple[str, ...]) -> bool:
    """Devuelve True si algún segmento o nombre de archivo está prohibido."""
    if not rel_parts:
        return True
    for part in rel_parts[:-1]:
        if part in FORBIDDEN_DIR_NAMES:
            return True
    filename = rel_parts[-1]
    if filename in FORBIDDEN_DIR_NAMES or filename in FORBIDDEN_FILE_NAMES:
        return True
    if filename.startswith(".env."):
        return True
    if filename.endswith(FORBIDDEN_SUFFIXES):
        return True
    return False


def _iter_tree_files(base_dir: Path) -> list[Path]:
    """Lista recursivamente los archivos válidos dentro de ``base_dir``."""
    files: list[Path] = []
    for path in sorted(base_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(base_dir).parts
        if _is_excluded(rel_parts):
            continue
        files.append(path)
    return files


# Enlaces e imágenes inline, con destino simple o entre <>, y título opcional.
MARKDOWN_LINK = re.compile(
    r"!?\[(?:\\.|[^\]\\])*\]\(\s*"
    r"(?P<target><[^>\n]*>|(?:\\.|[^\s()\\]|\((?:\\.|[^()\\])*\))+)"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)


def _relative_link_path(target: str) -> str | None:
    """Separa el ancla e ignora URLs, rutas absolutas y enlaces internos."""
    path = target.removeprefix("<").removesuffix(">")
    if not path or path.startswith(("#", "/")) or urlsplit(path).scheme:
        return None
    return path.split("#", 1)[0]


def _rewrite_despliegue_links(text: str, source: Path, repo_root: Path, arcname: str) -> str:
    """Adapta sólo los enlaces de parcial/ que apuntan al despliegue del repo."""
    def rewrite(match: re.Match[str]) -> str:
        target = match["target"]
        path = _relative_link_path(target)
        if path is None:
            return match[0]
        resolved = (source.parent / unquote(path)).resolve()
        try:
            relative = resolved.relative_to((repo_root / "despliegue").resolve())
        except ValueError:
            return match[0]
        destination = (Path("despliegue") / relative).as_posix()
        new_path = quote(posixpath.relpath(destination, posixpath.dirname(arcname)))
        new_target = target.replace(path, new_path, 1)
        start, end = match.span("target")
        return match[0][:start - match.start()] + new_target + match[0][end - match.start():]

    return MARKDOWN_LINK.sub(rewrite, text)


def build_entrega_zip(
    output_path: Path | None = None,
    group_name: str = DEFAULT_GROUP_NAME,
    repo_root: Path = REPO_ROOT,
) -> Path:
    """Construye ``Parcial_Cap1a6_<NombreDelGrupo>.zip`` y lo audita antes de retornar."""
    if output_path is None:
        output_path = repo_root / f"Parcial_Cap1a6_{group_name}.zip"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries_to_write: list[tuple[Path, str]] = []

    # 1. Archivos de parcial/ mapeados desde la raíz del repositorio
    for item_name in PARCIAL_ALLOWED_ROOT_ITEMS:
        source_path = repo_root / item_name
        if not source_path.exists():
            continue
        if source_path.is_file():
            if not _is_excluded((item_name,)):
                entries_to_write.append((source_path, f"parcial/{item_name}"))
        elif source_path.is_dir():
            for child_file in _iter_tree_files(source_path):
                rel_inside = child_file.relative_to(repo_root).as_posix()
                entries_to_write.append((child_file, f"parcial/{rel_inside}"))

    # 2. Archivos de despliegue/ mapeados desde repo_root / "despliegue"
    despliegue_dir = repo_root / "despliegue"
    if not despliegue_dir.is_dir():
        raise FileNotFoundError(f"No existe el directorio obligatorio: {despliegue_dir}")

    for child_file in _iter_tree_files(despliegue_dir):
        rel_inside = child_file.relative_to(despliegue_dir).as_posix()
        entries_to_write.append((child_file, f"despliegue/{rel_inside}"))

    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src_file, arcname in sorted(entries_to_write, key=lambda item: item[1]):
            if arcname.startswith("parcial/") and src_file.suffix == ".md":
                text = src_file.read_text(encoding="utf-8")
                zf.writestr(
                    arcname, _rewrite_despliegue_links(text, src_file, repo_root, arcname)
                )
            else:
                zf.write(src_file, arcname=arcname)

    verify_entrega_zip(output_path)
    return output_path


def verify_entrega_zip(zip_path: Path) -> dict[str, Any]:
    """Audita que el archivo ZIP cumpla la estructura y exclusiones de la consigna."""
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise FileNotFoundError(f"No existe el archivo ZIP a verificar: {zip_path}")

    with zipfile.ZipFile(zip_path, mode="r") as zf:
        names = [info.filename for info in zf.infolist() if not info.is_dir()]
        all_names = set(zf.namelist())

    if not names:
        raise ValueError("El archivo ZIP está vacío.")

    root_dirs = sorted({name.split("/", 1)[0] for name in names})
    if root_dirs != ["despliegue", "parcial"]:
        raise ValueError(
            f"Las carpetas raíz del ZIP deben ser exactamente ['despliegue', 'parcial'], "
            f"pero se encontraron: {root_dirs}"
        )

    for entry in names:
        parts = Path(entry).parts
        if len(parts) < 2:
            raise ValueError(f"Archivo suelto no permitido en la raíz del ZIP: {entry}")
        if _is_excluded(parts[1:]):
            raise ValueError(f"Entrada prohibida detectada en el ZIP: {entry}")

    name_set = set(names)
    missing = sorted(set(REQUIRED_ZIP_ENTRIES) - name_set)
    if missing:
        raise ValueError(
            f"Faltan archivos obligatorios dentro del ZIP: {', '.join(missing)}"
        )

    with zipfile.ZipFile(zip_path, mode="r") as zf:
        for entry in names:
            if not entry.endswith(".md"):
                continue
            text = zf.read(entry).decode("utf-8")
            for match in MARKDOWN_LINK.finditer(text):
                target = match["target"]
                path = _relative_link_path(target)
                if path is None:
                    continue
                resolved = posixpath.normpath(
                    posixpath.join(posixpath.dirname(entry), unquote(path))
                )
                directory = resolved.rstrip("/") + "/"
                if resolved not in all_names and not any(
                    name.startswith(directory) for name in all_names
                ):
                    raise ValueError(f"Enlace relativo roto en {entry}: {target}")

    parcial_count = sum(1 for n in names if n.startswith("parcial/"))
    despliegue_count = sum(1 for n in names if n.startswith("despliegue/"))

    return {
        "zip_path": str(zip_path),
        "root_dirs": root_dirs,
        "total_files": len(names),
        "parcial_files": parcial_count,
        "despliegue_files": despliegue_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera y verifica Parcial_Cap1a6_<NombreDelGrupo>.zip"
    )
    parser.add_argument(
        "--group",
        default=DEFAULT_GROUP_NAME,
        help="Nombre del grupo para el archivo ZIP (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta de salida opcional del archivo ZIP",
    )
    args = parser.parse_args()

    zip_path = build_entrega_zip(output_path=args.output, group_name=args.group)
    summary = verify_entrega_zip(zip_path)
    print(
        f"ZIP generado y verificado: {summary['zip_path']} "
        f"(total={summary['total_files']} archivos: "
        f"parcial={summary['parcial_files']}, despliegue={summary['despliegue_files']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
