# TP 1–4 en el VPS — Ejercicios 9 y 10

**URL pública:** https://api.ismaelsuarez.me · **Swagger:** https://api.ismaelsuarez.me/docs  
**Despliegue:** 2026-11-08, contenedor iniciado aproximadamente a las **20:23 UTC (17:23 hora Argentina, UTC−3)**, en Hostinger con Easypanel. Debe permanecer en línea **hasta la publicación de las notas**.

La hora de inicio se deriva del `docker ps` de las ≈20:37 UTC (`Up 14 minutes`) y los registros de arranque; no es una marca exacta de creación. La venta preliminar #3 tiene fecha `2026-11-08T20:33:33.863493Z`; la recreación D-04 fue aproximadamente a las 20:57 UTC, con comprobación externa de persistencia de #3 a las 20:58:32Z. La venta #4 de D-03, con el cuerpo exacto del TP y total `77000.00`, se registró a las 21:11 UTC; su comprobante D-08 aparece después del 201.

La [evidencia real D-01…D-08](evidencia/vps_ejercicio10.md) enlaza las capturas y las [salidas literales](evidencia/vps_transcript.txt), para permitir la corrección aun si la URL no estuviera disponible. Documenta también las diferencias respecto de los comandos literales de la consigna; no sustituye la obligación de mantener el servicio en línea.

Esta carpeta conserva únicamente el TP de capítulos 1 a 4 identificado en [PROCEDENCIA.md](PROCEDENCIA.md): aplicación, dos migraciones, configuración Alembic y seed. No incorpora usuarios, roles ni inventario del parcial; no usa Compose. PostgreSQL corre en un servicio separado de la aplicación.

## Configuración realizada en Easypanel

1. En el VPS de Hostinger (Ubuntu 24.04.4), crear el proyecto **`libreria`**.
2. Agregar el servicio PostgreSQL **`db`** (versión observada: 18.6), base **`libreria`**, usuario **`libreria`** y contraseña privada. Conservar el volumen persistente de datos del servicio. El destino interno es **`libreria_db:5432`**: sin dominio y sin puerto publicado.
3. Agregar la App **`api`**. En **Fuente → Git**, configurar:
   - Repositorio: `https://github.com/pabloavalos25/Actividad--ibreria-api.git`.
   - Rama: `master`; ruta de compilación: `/despliegue`.
   - En **Compilación**, elegir **Dockerfile**. Mantener **Auto Deploy apagado**.
4. Configurar el entorno de `api` de forma privada:
   ```text
   DATABASE_URL=postgresql+asyncpg://libreria:<CONTRASEÑA>@libreria_db:5432/libreria
   ECHO_SQL=false
   ```
   `<CONTRASEÑA>` es sólo un marcador. La URL que ofrece Easypanel usa `postgres://…?sslmode=disable`: cambiar el esquema a `postgresql+asyncpg://` y quitar `?sslmode=disable` para el driver asincrónico en esta red interna. Mantener usuario, base y host internos; codificar los caracteres especiales de la contraseña en la URL. No copiar valores reales al repositorio, imagen, ZIP ni evidencia; no capturar la pestaña **Entorno**.
5. En **Dominios**, agregar `api.ismaelsuarez.me`, ruta `/`, destino **HTTP**, puerto **8000**, ruta `/`. Activar **HTTPS con Let's Encrypt**. El proxy recibe 443 y reenvía a la aplicación por la red interna, sin publicar 8000.
6. Pulsar **Implementar**. Esperar el estado `healthy`; revisar en **Registros** las migraciones `846f445b2248` y `332ba12e013b`, seguidas del inicio de Uvicorn y `/health/ready` con 200.
7. Una vez saludable, abrir **Consola → Sh** del servicio `api` y ejecutar **una sola vez**:
   ```sh
   python seed.py
   ```
   Equivale al `docker exec libreria python seed.py` de la consigna, usando el contenedor real de Easypanel. La salida registrada confirma 3 editoriales, 3 géneros, 5 autores, 5 libros, 3 clientes (1 con perfil) y 2 ventas.

**No volver a ejecutar seed:** reemplaza los datos existentes, incluidas las ventas de prueba. No forma parte del arranque ni de una actualización.

## Equivalencia Easypanel ↔ Docker ↔ casos D

Los comandos manuales siguientes son una alternativa documentada, **no una transcripción de comandos ejecutados para desplegar**. Easypanel construyó y ejecutó la imagen `easypanel/libreria/api:latest` mediante Swarm.

| Acción en Easypanel / VPS real | Equivalente Docker manual | Caso |
|---|---|---|
| Fuente Git + `/despliegue` + builder Dockerfile; Implementar | `docker build --pull -t libreria-tp:ej9 ./despliegue` | D-01, D-02 |
| Entorno privado + servicio App; consultar estado y Registros | `docker run` con `--env-file` (abajo), `docker ps`, `docker logs libreria` | D-02, D-03 |
| Consola Sh: `python seed.py` | `docker exec libreria python seed.py` | Datos iniciales de D-03 |
| Eliminar el contenedor real; Swarm lo recrea con la configuración conservada | `docker rm -f libreria` y repetir el mismo `docker run` | D-04 |
| Pruebas SSH de imagen sin entorno y de su contenido | `docker run --rm <imagen>`; `--entrypoint ls` / `--entrypoint env` | D-05, D-06 |
| Consola/SSH sobre el contenedor real | `docker exec libreria id` | D-07 |
| Registros del servicio después del 201 de la venta | `docker logs libreria` | D-08 |

El nombre real fue `libreria_api.1.bkq3mdmbbsk62zxyjcyw9whlx`, no `libreria`; después de D-04 fue `libreria_api.1.zcc5484zjwby8rohpa55xy1w4`. La recreación fue automática tras `docker rm -f`, **no** un segundo `docker run` escrito a mano. D-03 documenta ready a las 20:33Z, el listado `GET /libros/` con 200 y cinco libros a las **21:05:40Z**, y la venta **#4** con el cuerpo exacto del TP a las **21:11 UTC** (cliente 2, libro 1 ×2 + libro 4 ×1, total `77000.00`). La venta #3 fue preliminar y acredita la persistencia en D-04, anterior a #4; ver la cronología exacta en la evidencia.

## Construir y ejecutar manualmente (equivalente)

Desde la raíz del repositorio, con Docker accesible:

```sh
docker build --pull -t libreria-tp:ej9 ./despliegue
docker image inspect python:3.12-alpine --format '{{.Size}}'
docker image inspect libreria-tp:ej9 --format '{{.Size}}'
```

El límite de 100 MB corresponde a la base, no al tamaño final. La instalación usa wheels (`--only-binary=:all:`), sin compiladores y sin caché de pip. El build falla si alguna dependencia no dispone de wheel compatible; no se agrega una toolchain implícitamente.

Guardar **fuera de `despliegue/` y del repositorio** el archivo de variables llamado **`libreria.env`**, siguiendo [env.example](env.example), con `DATABASE_URL` y `ECHO_SQL=false`. Su contenido no se reproduce aquí. El destino PostgreSQL debe ser alcanzable desde la red del contenedor; el nombre `libreria_db` pertenece a la red interna administrada por Easypanel y no se presupone resoluble en un Docker independiente.

```sh
ENV_FILE=/ruta/externa/libreria.env
APP_PORT=127.0.0.1:8000
docker run -d --name libreria --restart unless-stopped \
  --env-file "$ENV_FILE" -p "$APP_PORT:8000" libreria-tp:ej9
# En Linux, si PostgreSQL está en el host, agregar antes de la imagen:
# --add-host=host.docker.internal:host-gateway
docker inspect libreria --format '{{.State.Health.Status}}'
docker logs libreria
docker exec libreria id
```

`APP_PORT` incluye IP y puerto para limitar la publicación manual a loopback; requiere un proxy HTTPS para acceso público. **En el despliegue real Easypanel no publica 8000 en el host.** Dentro del contenedor, `localhost` identifica el propio contenedor; para una base del host se puede usar `host.docker.internal` con la opción Linux indicada, o el destino autorizado correspondiente.

El usuario `app` ejecuta migraciones y servidor sin privilegios. Cada inicio requiere URL, ejecuta `alembic upgrade head` y sólo si termina correctamente hace `exec uvicorn app.main:app --host 0.0.0.0 --port 8000`. No ejecuta seed automáticamente. Sin URL o con una base inaccesible, termina con error antes de iniciar HTTP; la política de reinicio puede volver a intentarlo.

El HEALTHCHECK ejecuta Python estándar cada cinco segundos contra `http://127.0.0.1:8000/health/ready`, con timeout de dos segundos. Una base caída hace fallar ready y la comprobación; un proceso iniciado no equivale a un contenedor saludable.

## Actualizar sin perder los datos

En Easypanel, con los cambios disponibles en `master`, pulsar **Implementar**: reconstruye la imagen y reemplaza el contenedor de `api`. Revisar `healthy` y los Registros. Auto Deploy permanece apagado.

Equivalente manual, conservando `ENV_FILE` y `APP_PORT` de la sección anterior:

```sh
docker build --pull -t libreria-tp:ej9 ./despliegue
docker stop libreria
docker rm libreria
docker run -d --name libreria --restart unless-stopped \
  --env-file "$ENV_FILE" -p "$APP_PORT:8000" libreria-tp:ej9
```

Los datos persisten en el **volumen del servicio `db`**, fuera del contenedor `api`. Alembic reconoce las dos revisiones aplicadas: en D-04 no aparecen líneas `Running upgrade` y la venta #3 sigue intacta. No borrar la base ni el volumen, ejecutar downgrade ni volver a cargar seed para actualizar. Si cambia la dirección de PostgreSQL, revisar la configuración antes de recrear.

## Red y seguridad

- Comprobación externa registrada: sólo **22, 80 y 443** abiertos entre los puertos probados; **3000, 5432 y 8000** cerrados/filtrados. No representa un barrido de todos los puertos.
- PostgreSQL sólo es accesible por la red interna de servicios. **Nunca publicar 5432** ni asignar un dominio público a `db`.
- Para inspección administrativa, usar únicamente un túnel **`ssh -L`** hacia un destino PostgreSQL alcanzable desde el VPS; no abrir el puerto de la base a Internet.
- Mantener credenciales fuera del repositorio, imagen, ZIP, capturas y logs. La evidencia D-06 muestra la imagen sin `.env` ni `DATABASE_URL` incorporada.
- El certificado observado es de Let's Encrypt; conservar HTTPS y el servicio disponibles hasta que se publiquen las notas.

## Cambios hechos al TP para correr en el contenedor

No se modificó su código funcional ni sus migraciones para contenerizarlo. Sólo se añadieron archivos Docker, arranque y salud; se reemplazó el ejemplo de entorno con marcadores sin credenciales de ejemplo y se actualizó esta documentación.

## Verificación local reproducible

```sh
# Desde la raíz, con PostgreSQL 17 instalado y requirements-dev.txt en .venv:
python scripts/test_docker.py
python -m pytest -q
```

El verificador crea una base PostgreSQL externa nueva, nombres de imágenes/contenedores propios y un archivo temporal fuera del contexto. No acepta una URL de base existente ni usa el `.env` habitual. Prueba construcción, usuario, ausencia de secretos incorporados, inicio fallido/sano, migraciones, salud y persistencia tras recreación. Limpia sólo sus recursos en `finally`. Las opciones y los resultados reales se registran en [evidencia/](evidencia/).

Los tests locales del shell y healthcheck permiten diagnosticar fallos sin Docker, pero no reemplazan la ejecución del contenedor.

### Evidencia histórica

La [simulación local previa](evidencia/ejercicio10_simulacion_local.md) y su [transcript](evidencia/vps_local_simulation.txt) se conservan como antecedentes. No prueban acceso público; la evidencia del VPS está en [vps_ejercicio10.md](evidencia/vps_ejercicio10.md).

## Referencias técnicas

- [Dockerfile oficial](https://docs.docker.com/reference/dockerfile/): ENTRYPOINT, USER y HEALTHCHECK.
- [Imagen oficial Python](https://hub.docker.com/_/python): variante Alpine.
