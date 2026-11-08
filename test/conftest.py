"""Configuración compartida para el checkout y la entrega extraída."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def pytest_configure(config):
    # Pytest crea basetemp, pero requiere que su directorio padre ya exista.
    basetemp = config.getoption('basetemp')
    if basetemp:
        Path(basetemp).resolve().parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope='session')
def deploy_dir():
    for candidate in (ROOT / 'despliegue', ROOT.parent / 'despliegue'):
        if candidate.is_dir():
            return candidate
    pytest.fail('Falta despliegue/ tanto dentro del proyecto como en la carpeta hermana')


@pytest.fixture(scope='session')
def git_checkout():
    if not (ROOT / '.git').exists():
        pytest.skip('Requiere el checkout Git; la entrega extraída no incluye .git')
