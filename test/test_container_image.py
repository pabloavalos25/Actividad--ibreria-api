import subprocess

import pytest


def test_install_dependencies_before_copying_only_tp_sources(deploy_dir):
    instructions = (deploy_dir / "Dockerfile").read_text().splitlines()
    assert instructions[0] == "FROM python:3.12-alpine"
    install = next(i for i, line in enumerate(instructions) if "pip install" in line)
    application = next(i for i, line in enumerate(instructions) if line.startswith("COPY app/"))
    assert install < application
    assert "--no-cache-dir" in instructions[install]
    assert "--only-binary=:all:" in instructions[install]
    assert not any("apk add" in line or line.startswith("COPY . ") for line in instructions)


def test_image_declares_unprivileged_start_and_health_without_credentials(deploy_dir):
    recipe = (deploy_dir / "Dockerfile").read_text()
    assert "USER app" in recipe
    assert 'ENTRYPOINT ["/app/docker-entrypoint.sh"]' in recipe
    assert 'CMD ["python", "/app/healthcheck.py"]' in recipe
    assert "DATABASE_URL" not in recipe
    assert "postgresql+asyncpg://" not in recipe
    assert len(list((deploy_dir / "migrations/versions").glob("*.py"))) == 2


@pytest.mark.usefixtures("git_checkout")
@pytest.mark.parametrize("filename", ["docker-entrypoint.sh", "Dockerfile"])
def test_container_start_files_keep_lf_after_windows_checkout(filename, deploy_dir):
    attribute = subprocess.check_output(
        ["git", "check-attr", "eol", "--", f"despliegue/{filename}"], cwd=deploy_dir.parent,
    ).decode().strip()
    assert attribute.endswith(": lf")
    assert b"\r" not in (deploy_dir / filename).read_bytes()
