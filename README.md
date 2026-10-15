# Librería API

![Python 3.13](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.143-green)
![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17-blue)

API REST asincrónica para el catálogo, los clientes y las ventas de una librería, con FastAPI, SQLModel y PostgreSQL.

TP de Programación III (UTN, Tecnicatura Universitaria en Programación a Distancia), unidades 1 a 4.

## Contenido

- [Stack](#stack)
- [Requisitos](#requisitos)
- [Puesta en marcha desde cero](#puesta-en-marcha-desde-cero)
- [Modelo de datos](#modelo-de-datos)
- [Endpoints](#endpoints)
- [Casos de prueba (C-01…C-08)](#casos-de-prueba-c-01c-08)
- [Reglas duras](#reglas-duras)
- [Estructura](#estructura)
- [Migraciones](#migraciones)
- [Troubleshooting (Windows)](#troubleshooting-windows)
- [Checklist de entrega](#checklist-de-entrega)
- [Integrantes](#integrantes)

## Stack

| Componente | Versión instalada | Mínimo |
|------------|-------------------|--------|
| Python | 3.13.7 | 3.12+ |
| PostgreSQL | 17.11 | 16+ |
| fastapi | 0.143.1 | — |
| sqlmodel | 0.0.24 | — |
| SQLAlchemy | 2.0.54 | 2.0+ |
| asyncpg | 0.32.0 | 0.30+ |
| alembic | 1.20.0 | 1.13+ |
| python-dotenv | 1.2.4 | 1.0+ |
| uvicorn | 0.54.0 | — |

Base local: `127.0.0.1:5432`, base `libreria`. Driver asíncrono `postgresql+asyncpg`.

## Requisitos

- Python 3.12 o superior.
- PostgreSQL 16 o superior (probado con 17), con la base `libreria` creada.
- En Windows: PowerShell y `psql` accesible. Si falta, instalar y agregar al PATH:

```powershell
winget install PostgreSQL.17
$env:PATH += ";C:\Program Files\PostgreSQL\17\bin"
```

> [!NOTE]
> En Windows los ejecutables (`psql`, `pg_isready`, `createdb`) están en `C:\Program Files\PostgreSQL\17\bin`. Sin esa carpeta en el PATH, PowerShell no los encuentra.

## Puesta en marcha desde cero

Todos los comandos se ejecutan desde la raíz del repositorio.

### 1. Entorno virtual

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Si PowerShell bloquea la activación, permitirlo solo en la sesión actual:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### 2. Dependencias

```bash
pip install -r requirements.txt
```

### 3. Base de datos

Crear una base vacía llamada `libreria`:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\createdb.exe" -h 127.0.0.1 -U postgres libreria
```

```bash
createdb -h 127.0.0.1 -U postgres libreria
```

Alternativa con Docker (si no hay PostgreSQL instalado):

```bash
docker run -d --name libreria-pg \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=libreria \
  -p 127.0.0.1:5432:5432 postgres:17
```

### 4. Archivo `.env`

```powershell
Copy-Item env.example .env
```

```bash
cp env.example .env
```

Editar `.env` y completar con usuario, clave, host y base propios.

> [!WARNING]
> El archivo `.env` no se versiona: nunca subas credenciales reales al repo.

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Dirección de la base con el driver asincrónico: `postgresql+asyncpg://usuario:clave@host:5432/libreria`. Obligatoria |
| `ECHO_SQL` | Con `true`, muestra en la consola las consultas emitidas. Opcional; por defecto `false` |

### 5. Esquema (solo Alembic)

```bash
alembic upgrade head
```

### 6. Datos iniciales

```bash
python seed.py
```

Vacía las tablas, reinicia los identificadores y carga siempre los mismos datos. Se puede correr las veces que haga falta para volver al estado inicial.

> [!WARNING]
> `seed.py` borra los datos existentes antes de cargar: úsalo solo en la base local de desarrollo.

### 7. Servidor

```bash
uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000` y la documentación interactiva en `http://127.0.0.1:8000/docs`.

Comprobación rápida:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

```bash
curl http://127.0.0.1:8000/health/live    # {"estado":"vivo"}
curl http://127.0.0.1:8000/health/ready   # {"estado":"ok","base":"disponible"}
```

## Modelo de datos

```mermaid
erDiagram
    editorial ||--o{ libro : publica
    genero ||--o{ libro : clasifica
    libro ||--o{ libro_autor : tiene
    autor ||--o{ libro_autor : firma
    cliente ||--|| perfil_cliente : posee
    cliente ||--o{ venta : realiza
    venta ||--o{ renglon_venta : contiene
    libro ||--o{ renglon_venta : integra

    editorial {
        int id PK
        string nombre
        string pais
    }
    genero {
        int id PK
        string nombre
    }
    autor {
        int id PK
        string nombre
        string nacionalidad
    }
    libro {
        int id PK
        string isbn
        string titulo
        decimal precio
        int stock
        int editorial_id FK
        int genero_id FK
    }
    libro_autor {
        int libro_id PK, FK
        int autor_id PK, FK
        string rol
        int orden
    }
    cliente {
        int id PK
        string nombre
        string email
    }
    perfil_cliente {
        int id PK
        int cliente_id FK
        string telefono
        string direccion
    }
    venta {
        int id PK
        int cliente_id FK
        datetime fecha
        decimal total
    }
    renglon_venta {
        int id PK
        int venta_id FK
        int libro_id FK
        int cantidad
        decimal precio_unitario
    }
```

- `libro → editorial` (N:1): todo libro pertenece a una editorial; una editorial publica muchos libros (`libro.editorial_id` obligatorio, con índice).
- `libro → genero` (N:1 opcional): el género puede ser nulo; un género agrupa muchos libros (`libro.genero_id` nullable, con índice; FK `fk_libro_genero_id` creada en la 2.ª migración).
- `autor ↔ libro` (N:M vía `libro_autor`): la tabla intermedia usa PK compuesta (`libro_id`, `autor_id`) y guarda `rol` (`autor`/`coautor`/`traductor`/`ilustrador`, con CHECK) y `orden` (≥ 1, con CHECK).
- `cliente → perfil_cliente` (1:1): el perfil es opcional por cliente pero único por `cliente_id` (UNIQUE `uq_perfil_cliente_cliente_id`); el segundo perfil da 409 (C-03).
- `cliente → venta` (1:N): cada venta tiene un solo cliente; un cliente acumula muchas ventas (ver `GET /clientes/{id}/ventas`).
- `venta → renglon_venta` (1:N con borrado en cascada): los renglones pertenecen a una sola venta y copian el `precio_unitario` del libro al momento de vender (el total lo calcula el servidor, C-06).
- `libro → renglon_venta` (1:N): un libro puede venderse en muchos renglones; el renglón guarda `cantidad` (> 0, con CHECK) y referencia histórica al libro vendido.

## Endpoints

Documentación interactiva: `http://127.0.0.1:8000/docs`. Paginación (RN-10) en todos los listados: `?limit=20&offset=0` (limit 1–100, por defecto 20; offset ≥ 0, por defecto 0).

| Módulo | Método y ruta | Éxito | Errores |
|--------|---------------|-------|---------|
| health | `GET /health/live` | 200 | — |
| health | `GET /health/ready` | 200 | — |
| editoriales | `POST /editoriales/` | 201 | 409 nombre repetido, 422 validación |
| editoriales | `GET /editoriales/` | 200 paginado | 422 paginación inválida |
| editoriales | `GET /editoriales/{id}` | 200 | 404, 422 id no entero |
| editoriales | `PATCH /editoriales/{id}` | 200 | 404, 409, 422 |
| editoriales | `GET /editoriales/{id}/libros` | 200 paginado | 404, 422 |
| generos | `POST /generos/` | 201 | 409 nombre repetido, 422 |
| generos | `GET /generos/` | 200 paginado | 422 |
| generos | `GET /generos/{id}/libros` | 200 paginado | 404, 422 |
| autores | `POST /autores/` | 201 | 409, 422 |
| autores | `GET /autores/{id}` | 200 | 404, 422 |
| autores | `PATCH /autores/{id}` | 200 | 404, 409, 422 |
| autores | `GET /autores/{id}/libros` | 200 paginado | 404, 422 |
| libros | `POST /libros/` | 201 | 409 (ISBN repetido o FK inválida), 422 |
| libros | `GET /libros/?titulo=&genero_id=&limit=&offset=` | 200 paginado | 422 |
| libros | `GET /libros/{id}` | 200 | 404, 422 |
| libros | `PATCH /libros/{id}` | 200 | 404, 409, 422 |
| clientes | `POST /clientes/` | 201 | 409 email repetido, 422 |
| clientes | `GET /clientes/{id}` | 200 | 404, 422 |
| clientes | `PATCH /clientes/{id}` | 200 | 404, 409, 422 |
| clientes | `POST /clientes/{id}/perfil` | 201 | 404, 409 ya tiene perfil, 422 |
| clientes | `GET /clientes/{id}/ventas` | 200 paginado | 404, 422 |
| ventas | `POST /ventas/` | 201 | 409 cliente/libros inválidos, 422 |
| ventas | `GET /ventas/` | 200 paginado | 422 |
| ventas | `GET /ventas/{id}` | 200 | 404, 422 |

Notas de diseño (no son errores):

> [!NOTE]
> Autores y clientes **no tienen listado** (`GET /autores/`, `GET /clientes/`): solo `GET /{id}`. Pedir el listado devuelve **405** por diseño. Géneros no tiene `GET /generos/{id}`: solo listado y `GET /generos/{id}/libros`. Ventas no tiene `PATCH`: las ventas no se modifican una vez registradas.

- 422 con id no entero (p. ej. `/libros/abc`) lo genera FastAPI sin ejecutar el handler.
- Ningún error expone texto de la base (RN-12): los 409 usan mensajes propios (ver casos C-02…C-05).

## Casos de prueba (C-01…C-08)

Archivos `.http` en `test/`, con la respuesta esperada en comentarios. Se ejecutan con la extensión **REST Client** de VS Code o el cliente HTTP de los IDE de JetBrains (abrir el archivo y usar *Send Request* en cada bloque `###`).

Antes de correrlos, dejar la base en el estado inicial:

```bash
python seed.py
```

| Caso | Archivo | Qué esperar |
|------|---------|-------------|
| C-01 · id no entero (`GET /libros/abc`) | `test/casos_errores.http` | 422, sin ejecutar el handler |
| C-02 · ISBN repetido / email repetido | `test/casos_errores.http` | 409 con mensaje propio (`...isbn invalidos` / `...ese email`) |
| C-03 · segundo perfil del cliente 1 | `test/casos_errores.http` | 409 `El cliente ya tiene un perfil` |
| C-04 · libro con editorial o autor inexistente | `test/casos_errores.http` | 409 `...editorial, genero, autor o isbn invalidos` |
| C-05 · venta con libro o cliente inexistente | `test/casos_errores.http` | 409 `...cliente o libros invalidos` |
| C-06 · venta válida con 2 renglones | `test/casos_venta.http` | 201, total `77000.00` calculado por el servidor |
| C-07 · detalle libro / venta | `test/casos_venta.http` | 200 y **2 consultas** en consola en cada lectura |
| C-08 · búsqueda con `' OR '1'='1` | `test/casos_errores.http` | 200 con lista vacía `[]` (parámetro ligado, sin inyección) |

C-06 agrega una venta cada vez que se ejecuta; el resto solo lee y se puede repetir. Para C-07, arrancar el servidor con el diagnóstico activado:

> [!TIP]
> Sin `ECHO_SQL=true` no verás las consultas: debe estar activo en la misma sesión que lanza `uvicorn` (y reiniciar el servidor).

```powershell
$env:ECHO_SQL = "true"; uvicorn app.main:app
```

```bash
ECHO_SQL=true uvicorn app.main:app
```

La evidencia está en `test/evidencia_c07.md`: fragmento de consola con las 2 consultas por lectura (misma cantidad con uno o varios autores/renglones, sin N+1).

## Reglas duras

De `ROADMAP.md`, no negociables:

- Tablas y columnas con nombres exactos (los usan los tests); no renombrar ni quitar.
- Dinero con `Decimal` (NUMERIC), nunca `float`.
- Sin `create_all`: el esquema se crea solo con Alembic (plantilla asíncronica).
- Sin credenciales reales en el repo; `.env` no se sube.
- Ningún error expone texto de la base (RN-12).
- Handlers `async def`, sin llamadas bloqueantes; lazy loading prohibido (lecturas con `joinedload`/`selectinload`).
- Paginación RN-10 con `limit`/`offset` en todos los listados.

## Estructura

```text
app/
├── main.py              aplicación, ciclo de vida y registro de routers
├── core/                configuración, motor y sesión, traducción de errores
└── modules/             un módulo por recurso, todos con la misma estructura
    └── <módulo>/
        ├── models.py    modelos de tabla, restricciones y relaciones
        ├── schemas.py   contratos de entrada y de salida
        ├── service.py   lógica, traducción de errores y lecturas con precarga
        └── router.py    rutas HTTP
migrations/              configuración de Alembic y sus versiones
test/                    casos .http y evidencia_c07.md
seed.py                  carga del estado inicial
```

Módulos: `health`, `editoriales`, `generos`, `autores`, `libros`, `clientes` y `ventas`.

## Migraciones

```bash
alembic upgrade head     # aplica todas las migraciones
alembic downgrade -1     # deshace la última
alembic current          # muestra la revisión aplicada
python seed.py           # datos iniciales (se repite cuando haga falta)
```

Flujo: `upgrade head` → `seed.py` → `uvicorn` → probar. `downgrade -1` solo para verificar/desha­cer la última revisión.

## Troubleshooting (Windows)

<details>
<summary>Ver síntomas y soluciones</summary>

| Síntoma | Causa probable | Comando / solución |
|---------|----------------|--------------------|
| Puerto 8000 ocupado (`Address already in use`) | Otro `uvicorn` corriendo | `netstat -ano \| findstr :8000` y cerrar ese PID, o usar otro puerto: `uvicorn app.main:app --port 8001` |
| No conecta a Postgres | Servicio caído o credenciales | `& "C:\Program Files\PostgreSQL\17\bin\pg_isready.exe" -h 127.0.0.1 -p 5432` debe responder `accepting connections`; si no, iniciar el servicio PostgreSQL |
| `alembic upgrade head` no cambia nada / error de revisión | Revisión desfasada | `alembic current` y comparar con `migrations/versions/`; aplicar `upgrade head` desde la raíz del repo con el `.env` correcto |
| No se ven consultas en C-07 | `ECHO_SQL` no activo | Arrancar con `$env:ECHO_SQL = "true"` en la misma sesión de PowerShell (o `ECHO_SQL=true` en bash); reiniciar el servidor |
| `psql` / `createdb` no se reconocen | PATH sin PostgreSQL | Agregar `C:\Program Files\PostgreSQL\17\bin` al PATH (ver Requisitos) |
| `.venv` no se activa | ExecutionPolicy | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` y reintentar `.\.venv\Scripts\Activate.ps1` |

</details>

## Checklist de entrega

<details>
<summary>Ver checklist</summary>

- [ ] `pip install -r requirements.txt` OK en entorno limpio.
- [ ] `alembic upgrade head` crea el esquema desde cero.
- [ ] `python seed.py` deja el estado inicial reproducible.
- [ ] `uvicorn app.main:app` levanta; 200 en `/health/live` y `/health/ready`.
- [ ] Los 8 casos (C-01…C-08) dan lo esperado desde `test/*.http`.
- [ ] `test/evidencia_c07.md` con las 2 consultas por lectura.
- [ ] Sin `.env` ni credenciales en el repo; sin `create_all`; dinero con `Decimal`.

</details>

## Integrantes

Trabajo grupal — Programación III (UTN), unidades 1 a 4.

| Pablo Avalos | Ismael Suarez | Sofia Blangetti |
|:---:|:---:|:---:|
