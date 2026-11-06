# Contenedor del TP original — ejercicio 9

Esta carpeta conserva el TP de capítulos 1 a 4 identificado en [PROCEDENCIA.md](PROCEDENCIA.md). El Dockerfile usa únicamente su aplicación, sus dos migraciones, configuración Alembic y seed. No incorpora usuarios, roles ni inventario del parcial. PostgreSQL es externo: no se usa Compose ni un contenedor de base.

## Preparar configuración

Guardar el archivo de entorno **fuera de `despliegue/`** y del repositorio, tomando como referencia [env.example](env.example). Reemplazar sus marcadores por datos del destino autorizado; codificar caracteres especiales del usuario o contraseña en la URL. No versionar ni mostrar ese archivo en evidencia.

Se requieren `DATABASE_URL` con driver `postgresql+asyncpg` y `ECHO_SQL=false`. Dentro del contenedor, `localhost` identifica el propio contenedor. Para PostgreSQL del host, Docker Desktop ofrece `host.docker.internal`; en Linux agregar `--add-host=host.docker.internal:host-gateway`. Si la cátedra entrega otra dirección, usar esa dirección.

## Construir y ejecutar

Desde la raíz del repositorio, con Docker accesible:

```sh
docker build --pull -t libreria-tp:ej9 ./despliegue
docker image inspect python:3.12-alpine --format '{{.Size}}'
docker image inspect libreria-tp:ej9 --format '{{.Size}}'
```

El límite de 100 MB corresponde a la base, no al tamaño final. La instalación usa wheels (`--only-binary=:all:`), sin compiladores y sin caché de pip. El build falla si alguna dependencia no dispone de wheel compatible; no se agrega una toolchain implícitamente.

Completar las dos variables siguientes con el archivo externo y el puerto asignado antes de ejecutar. Los valores de ejemplo son marcadores, no un despliegue realizado:

```sh
ENV_FILE=/ruta/externa/libreria.env
APP_PORT=PUERTO_ASIGNADO
docker run -d --name libreria --restart unless-stopped \
  --env-file "$ENV_FILE" -p "$APP_PORT:8000" libreria-tp:ej9
# En Linux, si PostgreSQL está en el host, agregar antes de la imagen:
# --add-host=host.docker.internal:host-gateway
docker inspect libreria --format '{{.State.Health.Status}}'
docker logs libreria
docker exec libreria id
```

Se publica sólo el puerto de aplicación. El usuario `app` ejecuta tanto migraciones como servidor sin privilegios. Cada inicio requiere URL, ejecuta `alembic upgrade head` y sólo si termina correctamente hace `exec uvicorn app.main:app --host 0.0.0.0 --port 8000`. No se ejecuta seed automáticamente. Una URL ausente o una base inaccesible termina el proceso con error antes de iniciar HTTP; con la política de reinicio Docker puede volver a intentarlo.

El HEALTHCHECK ejecuta Python estándar cada cinco segundos contra `http://127.0.0.1:8000/health/ready`, con timeout de dos segundos. Una base caída hace fallar ready y la comprobación; un proceso iniciado no equivale a un contenedor saludable.

## Verificación local reproducible

```sh
# Desde la raíz, con PostgreSQL 17 instalado y requirements-dev.txt en .venv:
python scripts/test_docker.py
python -m pytest -q
```

El verificador crea una base PostgreSQL externa nueva, nombres de imágenes/contenedores propios y un archivo temporal fuera del contexto. No acepta una URL de base existente ni usa el `.env` habitual. Prueba construcción, usuario, ausencia de secretos incorporados, inicio fallido/sano, migraciones, salud y persistencia tras recreación. Limpia sólo sus recursos en `finally`. Las opciones y los resultados reales se registran en [evidencia/](evidencia/).

Los tests locales del shell y healthcheck permiten diagnosticar fallos sin Docker, pero no reemplazan la ejecución del contenedor.

## Actualizar sin perder los datos externos

```sh
docker build --pull -t libreria-tp:ej9 ./despliegue
docker stop libreria
docker rm libreria
docker run -d --name libreria --restart unless-stopped \
  --env-file "$ENV_FILE" -p "$APP_PORT:8000" libreria-tp:ej9
```

Usar el mismo destino PostgreSQL conserva los datos. Alembic reconoce las dos revisiones ya aplicadas. No borrar la base, ejecutar downgrade ni volver a cargar seed para actualizar la imagen. Si cambia la dirección externa del PostgreSQL, revisar el run antes de recrear.

## Correcciones del TP

No se modificó su código funcional ni sus migraciones para contenerizarlo. Sólo se añadieron archivos Docker, arranque y salud; se reemplazó el ejemplo de entorno con marcadores sin credenciales de ejemplo y se actualizó esta documentación.

## Ejercicio 10 pendiente

URL pública: pendiente. Fecha/hora de despliegue: pendiente. Host, puerto asignado y credenciales: deben ser provistos fuera del repositorio. No se realizó despliegue ni seed en VPS. Los casos D-02/D-03/D-04/D-08 deben ejecutarse allí; la evidencia local no certifica accesibilidad desde Internet ni permanencia hasta las notas.

Antes de ejecutar seed sobre el servidor se debe confirmar expresamente su destino y la autorización para reemplazar los datos. Las contraseñas reales nunca se guardan en DEPLOY.md ni en logs versionados.

## Referencias técnicas

- [Dockerfile oficial](https://docs.docker.com/reference/dockerfile/): ENTRYPOINT, USER y HEALTHCHECK.
- [Imagen oficial Python](https://hub.docker.com/_/python): variante Alpine.
