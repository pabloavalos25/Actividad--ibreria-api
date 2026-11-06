#!/bin/sh
set -eu

: "${DATABASE_URL:?Falta DATABASE_URL en el entorno externo}"
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
