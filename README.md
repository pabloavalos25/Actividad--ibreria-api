# Librería API — Parcial Capítulos 1 a 6

API REST asincrónica desarrollada con FastAPI, SQLModel, SQLAlchemy 2.0 (`asyncpg`) y PostgreSQL 16+ para la gestión del catálogo, el inventario de sólo agregado, los clientes, las ventas atómicas y el control de acceso con usuarios, roles con vigencia y auditoría de seguridad. Continúa el Trabajo Práctico de los capítulos 1 a 4 de **Programación III** (UTN) y lo extiende hasta el capítulo 6 (*Del objeto a la transacción*).

**Integrantes del grupo:** Pablo Avalos, Ismael Suarez y Sofia Blangetti.

---

## 1. Organización de los dos entregables

El repositorio organiza por separado las dos carpetas exigidas por la consigna:

- **Raíz del repositorio (`parcial/` al armar el `.zip`)**: contiene el proyecto ampliado con los cambios de los capítulos 5 y 6 (14 tablas, 4 migraciones de Alembic, autenticación `bcrypt` + JWT en cookie `HttpOnly`, RBAC en base de datos, repositorios y `UnitOfWork`, inventario de sólo agregado, lecturas sin N+1, `seed.py`, colección `.http` `C-01` a `C-16`, `test/solo_agregado.sql` y `evidencia/`).
- **[`despliegue/`](despliegue/DEPLOY.md)**: conserva intacto el Trabajo Práctico de los capítulos 1 a 4 junto con el `Dockerfile` sobre `python:3.12-alpine`, `.dockerignore`, `docker-entrypoint.sh`, `healthcheck.py`, `env.example`, `DEPLOY.md` y `despliegue/evidencia/` (`D-01` a `D-08`).

Ninguna de las dos carpetas incluye `.venv`, `__pycache__`, `.pytest_cache`, `tmp/`, `.env` ni credenciales reales.

---

## 2. Puesta en marcha rápida desde cero

**Requisitos previos:** Python 3.12+ y PostgreSQL 16+ con una base vacía creada (por ejemplo, `libreria`).

### Linux / macOS (`bash`)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Completar en `.env` las credenciales de PostgreSQL (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`) y pegar el valor generado en `JWT_SECRET`. Luego aplicar las migraciones, cargar el estado inicial y levantar el servidor:

```bash
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

### Windows (`PowerShell`)

```powershell
py -3 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item env.example .env
& ./.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
& ./.venv/Scripts/python.exe -m alembic upgrade head
& ./.venv/Scripts/python.exe seed.py
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

- **API**: `http://127.0.0.1:8000`
- **Documentación interactiva (OpenAPI)**: `http://127.0.0.1:8000/docs`
- **Salud**:
  - `GET http://127.0.0.1:8000/health/live` → `200 OK` (`{"status": "ok"}`, sin consultar la base).
  - `GET http://127.0.0.1:8000/health/ready` → `200 OK` ejecuta `SELECT 1` contra PostgreSQL (`503 Service Unavailable` con mensaje propio si la base no responde).

---

## 3. Variables de entorno (`env.example` y `app/core/config.py`)

`Settings(BaseSettings)` lee variables del entorno de proceso y del archivo `.env` (con prioridad para las de proceso) y construye `database_url` mediante `@computed_field` y `URL.create("postgresql+asyncpg", ...)`. En este proyecto ampliado **ya no se utiliza `DATABASE_URL` directa** (que sí conserva `despliegue/` para el TP 1–4).

| Variable | Descripción | Valor por defecto | Obligatoria / Sensible |
|----------|-------------|-------------------|------------------------|
| `POSTGRES_USER` | Usuario de conexión a PostgreSQL | — | Obligatoria |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL (`SecretStr`, oculta en trazas y `repr`) | — | Obligatoria / Sensible |
| `POSTGRES_DB` | Nombre de la base de datos (ej. `libreria`) | — | Obligatoria |
| `POSTGRES_HOST` | Host del servidor PostgreSQL (ej. `127.0.0.1`) | — | Obligatoria |
| `POSTGRES_PORT` | Puerto de PostgreSQL | `5432` | Opcional |
| `JWT_SECRET` | Clave secreta para firmar y verificar tokens JWT HS256 (`SecretStr`) | — | Obligatoria / Sensible |
| `SQL_ECHO` | Muestra en consola las sentencias SQL ejecutadas (admite alias `ECHO_SQL`) | `false` | Opcional |
| `DB_POOL_SIZE` | Conexiones base del pool asincrónico (`>= 1`) | `5` | Opcional |
| `DB_MAX_OVERFLOW` | Conexiones adicionales máximas sobre `DB_POOL_SIZE` (`>= 0`) | `10` | Opcional |
| `BCRYPT_ROUNDS` | Factor de costo (rondas) de `bcrypt` (`4..31`) | `12` | Opcional |
| `BCRYPT_CONCURRENCY` | Máximo de operaciones `bcrypt` simultáneas en el semáforo (`>= 1`) | `4` | Opcional |
| `JWT_TTL_SECONDS` | Tiempo de vida del JWT y `Max-Age` de la cookie `access_token` en segundos | `1800` | Opcional |
| `COOKIE_SECURE` | Activa el atributo `Secure` en la cookie `access_token` (`true` bajo HTTPS) | `false` | Opcional |

---

## 4. Estado inicial (`python seed.py`)

El esquema se crea exclusivamente con `alembic upgrade head` (4 revisiones en `migrations/versions/`: las 2 del TP más `3e5d56535b0e` para tablas de acceso, stock, vínculo cliente-usuario e índice parcial de ISBN, y `a05a50bc58a8` escrita a mano para el disparador `trg_movimiento_stock_inmutable`). Nunca se utiliza `create_all`.

`python seed.py` trunca las 14 tablas en orden seguro (`RESTART IDENTITY CASCADE`), calcula los hashes `bcrypt` fuera del bucle de eventos antes de abrir la transacción y carga el estado inicial determinístico:

### Usuarios iniciales (contraseña común: `secreto123`)

| ID | Nombre | Email | Rol vigente | `debe_cambiar_password` | Vínculo con `cliente` |
|----|--------|-------|-------------|-------------------------|-----------------------|
| `1` | Ada Lovelace | `admin@example.com` | `ADMIN` | `false` | — |
| `2` | Alan Turing | `admin2@example.com` | `ADMIN` | `false` | — |
| `3` | Carlos Venta | `vendedor@example.com` | `VENDEDOR` | `false` | — |
| `4` | Ana Paz | `ana@example.com` | `CLIENTE` | `false` | `cliente.id = 3` (`Ana Paz`) |
| `5` | Nuevo Ingreso | `nuevo@example.com` | `VENDEDOR` | `true` | — |

### Catálogo, clientes, venta e inventario inicial

- **3 editoriales** (`Sudamericana`, `Emecé`, `Anagrama`), **3 géneros** (`Ficción`, `Cuento`, `Ensayo`) y **6 autores** (`Julio Cortázar`, `Jorge Luis Borges`, `Adolfo Bioy Casares`, `Silvina Ocampo`, `Ricardo Piglia`, `Mariana Enríquez`).
- **5 libros vigentes** (dejando libre el ISBN `978-950-00-0006-6` para pruebas de alta):
  1. `Rayuela` (`978-950-00-0001-1`, `$25000.00`, `stock = 10`)
  2. `Antología de la literatura fantástica` (`978-950-00-0002-2`, `$30000.00`, `stock = 5`, 3 coautores)
  3. `Ficciones` (`978-950-00-0003-3`, `$22000.00`, `stock = 8`)
  4. `Respiración artificial` (`978-950-00-0004-4`, `$27000.00`, `stock = 3`)
  5. `Bestiario` (`978-950-00-0005-5`, `$19500.00`, `stock = 1`, autor + prologuista)
- **3 clientes**: `Lucía Fernández` (`id=1`, con perfil), `Tomás Ríos` (`id=2`, sin cuenta de usuario) y `Ana Paz` (`id=3`, vinculada a `usuario_id=4`).
- **Venta 1**: de `Lucía Fernández` por `$69000.00` (`1 × Rayuela` + `2 × Ficciones`).
- **7 movimientos de stock** (5 ingresos iniciales `+11, +5, +10, +3, +1` registrados por `usuario_id=1` y 2 egresos `-1, -2` de la `Venta 1` registrados por `usuario_id=3`), cumpliendo `libro.stock == SUM(movimiento_stock.cantidad)` en los 5 libros.
- **1 evento de seguridad**: `actor="SISTEMA"`, `accion="Carga de los datos iniciales"`.

---

## 5. Arquitectura y reglas de dominio (Ejercicios 1 a 8)

- **Capas por módulo (`Router → Service → UoW → Repository → Model`)**:
  - `BaseRepository[T]` y `SoftDeleteRepository[T]` (en `app/core/repository.py`) reciben la sesión y la clase del modelo en su constructor, precargan relaciones (`joinedload` / `selectinload`) y hacen `flush()` sin `commit()`.
  - Cada operación de escritura se ejecuta dentro de `async with uow:` compartiendo la sesión de la petición. Los servicios reciben el `UnitOfWork` ya construido por el router.
- **Autenticación y límite de intentos (`app/core/security.py` y `app/modules/usuarios/`)**:
  - `bcrypt` corre en `asyncio.to_thread` bajo `asyncio.Semaphore(BCRYPT_CONCURRENCY)` sin transacción abierta y rechaza con `422` contraseñas que superen 72 bytes en UTF-8.
  - Cinco intentos fallidos para el mismo `(email, ip)` en 60 segundos devuelven `429 Too Many Requests` con `Retry-After` en el sexto intento antes de ejecutar `bcrypt`.
  - Ante un correo inexistente se verifica contra un hash ficticio precalculado en `lifespan` y se devuelve el mismo mensaje `401`.
  - Cada intento de login se persiste en `intento_acceso` usando una sesión y transacción independientes para sobrevivir al rollback del `401`.
  - El JWT viaja exclusivamente en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`); no se entrega en el cuerpo ni se lee de `Authorization: Bearer`.
- **Autorización y dos grupos de rutas (`app/main.py` y `app/core/dependencies.py`)**:
  - Grupo público (`/health/*`, `/auth/*` y lecturas públicas del catálogo) y grupo protegido con control único de `debe_cambiar_password` (`403` fuera de `/auth` hasta ejecutar `POST /auth/cambiar-password`).
  - `requiere_rol` consulta las filas vigentes de `asignacion_rol` en la base en cada petición (los roles del JWT en `/auth/yo` son sólo informativos).
  - Un `ADMIN` no puede revocar su propio `ADMIN` ni dejar al sistema sin administradores vigentes (`409`).
- **Inventario de sólo agregado, baja lógica y lecturas sin N+1 (`app/modules/libros/` y `app/modules/ventas/`)**:
  - Todo cambio de existencias pasa por el punto único `modificar_stock`, que actualiza `libro.stock` y agrega la fila en `movimiento_stock` en la misma transacción.
  - El disparador PostgreSQL `trg_movimiento_stock_inmutable` rechaza cualquier `UPDATE` o `DELETE` sobre `movimiento_stock` (`SQLSTATE 23514`).
  - `DELETE /libros/{id}` aplica baja lógica (`eliminado_en`), oculta el libro de los listados y permite reutilizar su ISBN gracias al índice único parcial `uq_libro_isbn_vigente` (`WHERE eliminado_en IS NULL`), conservando el título en las ventas históricas.
  - Al confirmar `POST /ventas/`, `BackgroundTasks` agenda el envío cooperativo (`asyncio.sleep(0.5)`) del comprobante en consola.

Detalles adicionales en [docs/PERSISTENCIA.md](docs/PERSISTENCIA.md), [docs/PROGRESO_PARCIAL_CAP1A6.md](docs/PROGRESO_PARCIAL_CAP1A6.md) y [docs/REQUISITOS_PARCIAL_CAP1A6.md](docs/REQUISITOS_PARCIAL_CAP1A6.md).

---

## 6. Guía de verificación de los casos `C-01` a `C-16` y evidencias

Antes de ejecutar cualquiera de los dos archivos `.http` (con la extensión **REST Client** de VS Code o el cliente HTTP de JetBrains), restaurar el estado inicial con `python seed.py`:

| Caso | Qué demuestra | Archivo ejecutable en `test/` | Evidencia complementaria |
|------|---------------|-------------------------------|--------------------------|
| **C-01** | Parámetro de ruta no entero (`GET /libros/abc`) con sesión iniciada → `422` sin ejecutar handler | `test/casos_acceso_autorizacion.http` | — |
| **C-02** | Auto-registro `201`; colisión de correo en `usuario` (`ana@example.com`) o en `cliente` (`lucia@example.com`) → `409` sin filas sueltas | `test/casos_acceso_autorizacion.http` | — |
| **C-03** | Login devuelve `Set-Cookie` (`HttpOnly`, `SameSite=Lax`, `Max-Age`) y cuerpo sin token; sin cookie o con `Authorization: Bearer` → `401` | `test/casos_acceso_autorizacion.http` | — |
| **C-04** | Login con correo existente y clave mala vs correo inexistente → mismo cuerpo `401` y tiempo comparable | `test/casos_acceso_autorizacion.http` | — |
| **C-05** | Seis intentos fallidos seguidos → los primeros 5 dan `401` (registrados en `intento_acceso`) y el sexto responde `429` con `Retry-After` en pocos ms | `test/casos_acceso_autorizacion.http` | — |
| **C-06** | Sin sesión `401`; `VENDEDOR` intentando crear libro `403`; `CLIENTE` (`ana@example.com`) ve su propia venta (`200`) y no la ajena (`403`) | `test/casos_acceso_autorizacion.http` | — |
| **C-07** | Múltiples sesiones con `# @name` y `# @no-cookie-jar`; revocar rol con sesión abierta → siguiente pedido `403`, `/auth/yo` muestra diferencia DB vs token, fila revocada permanece; `vence_en` pasado o sin zona → `422` | `test/casos_acceso_autorizacion.http` | — |
| **C-08** | Autoprotección: `ADMIN` intentando revocar su propio `ADMIN` → `409` | `test/casos_acceso_autorizacion.http` | — |
| **C-09** | `nuevo@example.com` bloqueado con `403` salvo en `/auth`; tras `POST /auth/cambiar-password`, la misma cookie sirve en rutas protegidas (`200`) | `test/casos_acceso_autorizacion.http` | — |
| **C-10** | Venta válida con 2 renglones → `201` con precios copiados y total calculado, stock descontado, movimientos negativos creados y aviso en consola 0,5 s después | `test/casos_ventas_stock_catalogo.http` | `evidencia/ej8_comprobante.md` |
| **C-11** | Venta con `Rayuela` (1 ejemplar, alcanza) y `Bestiario` (2 ejemplares, hay 1) → `409` todo-o-nada; `Rayuela` sigue en `10` y sin movimientos parciales | `test/casos_ventas_stock_catalogo.http` | — |
| **C-12** | Venta con cliente inexistente, libro inexistente o libro dado de baja → `409` en los tres casos sin escrituras | `test/casos_ventas_stock_catalogo.http` | — |
| **C-13** | Reponer libro (`200` con movimiento); dar de baja `Ficciones` (`204`, desaparece del catálogo, `409` al vender/reponer); reutilizar su ISBN (`201`); segundo vigente con ese ISBN (`409`); `GET /ventas/1` conserva el título | `test/casos_ventas_stock_catalogo.http` | — |
| **C-14** | `UPDATE` y `DELETE` sobre `movimiento_stock` en `psql` rechazados por el disparador (`SQLSTATE 23514`), dejando la fila intacta | `test/solo_agregado.sql` y `test/casos_ventas_stock_catalogo.http` | `evidencia/ej7_integridad.md` y `evidencia/c14_psql.txt` |
| **C-15** | Detalle de venta con 2 renglones y con 4 renglones (`SQL_ECHO=true`) ejecuta la misma cantidad fija de consultas `SELECT` | `test/casos_ventas_stock_catalogo.http` | `evidencia/ej8_lecturas.md` |
| **C-16** | Búsqueda con `' OR '1'='1` (`total: 0`), `titulo=ficc&size=1` (`total: 1`, `pages: 1`), `page=2` (`422`), `size=500` (`422`), `PATCH` parcial de `precio` (`200`) y `PATCH` con `stock` (`422`) | `test/casos_ventas_stock_catalogo.http` | — |

Para ejecutar directamente en `psql` la verificación de sólo agregado (`C-14`):

```bash
psql -X --no-password -h 127.0.0.1 -p 5432 -U postgres -d libreria \
  -v movimiento_id=1 -f test/solo_agregado.sql
```

---

## 7. Ejecución de la suite de pruebas automatizadas (`pytest`)

Para correr las pruebas automatizadas instalar también `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
python -m pytest test/ -q
```

Para ejecutar el verificador integral sobre una instancia temporal aislada de PostgreSQL (que valida `upgrade head → downgrade base → upgrade head`, `alembic check` y la suite `postgres_tests/`):

```bash
python scripts/test_postgres.py
```
