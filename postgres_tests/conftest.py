import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser):
    parser.addoption('--postgres-config', help='JSON del cluster temporal propio dentro de tmp/')


@pytest.fixture(scope='session')
def pg_config(request):
    filename = request.config.getoption('--postgres-config')
    if not filename:
        raise pytest.UsageError('Estas pruebas requieren --postgres-config del cluster aislado; no se omiten.')
    filename = Path(filename).resolve()
    if not filename.is_relative_to(ROOT / 'tmp'):
        raise pytest.UsageError('La configuración de pruebas debe estar dentro de tmp/ del proyecto.')
    config = json.loads(filename.read_text(encoding='utf-8'))
    data = Path(config['data_directory']).resolve()
    if not (data.is_relative_to(ROOT / 'tmp') and config['owner'] == 'parcial-ej2-tests'
            and config['host'] == '127.0.0.1' and config['port'] != 5432
            and config['user'].startswith('parcial_') and config['database'].startswith('parcial_')):
        raise pytest.UsageError('Destino de pruebas no reconocido como cluster aislado propio.')
    return config
