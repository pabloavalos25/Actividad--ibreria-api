FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt
RUN addgroup -S app && adduser -S -G app app
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini seed.py docker-entrypoint.sh healthcheck.py ./
RUN chmod 755 /app/docker-entrypoint.sh
USER app
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 CMD ["python", "/app/healthcheck.py"]
ENTRYPOINT ["/app/docker-entrypoint.sh"]
