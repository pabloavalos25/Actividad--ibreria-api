from pathlib import Path
import subprocess

import pytest


DEPLOY = Path(__file__).resolve().parents[1] / "despliegue"


def test_install_dependencies_before_copying_only_tp_sources():
    instructions = (DEPLOY / "Dockerfile").read_text().splitlines()
    assert instructions[0] == "FROM python:3.12-alpine"
    install = next(i for i, line in enumerate(instructions) if "pip install" in line)
    application = next(i for i, line in enumerate(instructions) if line.startswith("COPY app/"))
    assert install < application
    assert "--no-cache-dir" in instructions[install]
    assert "--only-binary=:all:" in instructions[install]
    assert not any("apk add" in line or line.startswith("COPY . ") for line in instructions)


def test_image_declares_unprivileged_start_and_health_without_credentials():
    recipe = (DEPLOY / "Dockerfile").read_text()
    assert "USER app" in recipe
    assert 'ENTRYPOINT ["/app/docker-entrypoint.sh"]' in recipe
    assert 'CMD ["python", "/app/healthcheck.py"]' in recipe
    assert "DATABASE_URL" not in recipe
    assert "postgresql+asyncpg://" not in recipe
    assert len(list((DEPLOY / "migrations/versions").glob("*.py"))) == 2


@pytest.mark.parametrize("filename", ["docker-entrypoint.sh", "Dockerfile"])
def test_container_start_files_keep_lf_after_windows_checkout(filename):
    attribute = subprocess.check_output(
        ["git", "check-attr", "eol", "--", f"despliegue/{filename}"], cwd=DEPLOY.parent,
    ).decode().strip()
    assert attribute.endswith(": lf")
    assert b"\r" not in (DEPLOY / filename).read_bytes()
