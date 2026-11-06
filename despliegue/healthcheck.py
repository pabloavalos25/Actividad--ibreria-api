"""Salud del contenedor: requiere respuesta correcta de la base vía ready."""

from urllib.error import URLError
from urllib.request import urlopen


def check_ready(url: str = 'http://127.0.0.1:8000/health/ready') -> int:
    try:
        with urlopen(url, timeout=2) as response:
            return 0 if response.status == 200 else 1
    except (OSError, URLError):
        return 1


if __name__ == '__main__':
    raise SystemExit(check_ready())
