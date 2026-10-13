# Librería API

API REST asincrónica para el catálogo, los clientes y las ventas de una librería, con FastAPI, SQLModel y PostgreSQL.

Trabajo práctico de Programación III (UTN, Tecnicatura Universitaria en Programación a Distancia), unidades 1 a 4.

## Requisitos

- Python 3.12 o superior
- PostgreSQL 16 o superior

## Puesta en marcha desde cero

Todos los comandos se ejecutan desde la raíz del repositorio.

### 1. Entorno virtual

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Dependencias

```bash
pip install -r requirements.txt
```

### 3. Base de datos

Crear una base vacía llamada `libreria` en PostgreSQL.

Si no hay un PostgreSQL instalado, se puede levantar uno con Docker:

```bash
docker run -d --name libreria-pg \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=libreria \
  -p 127.0.0.1:5432:5432 postgres:17
```

### 4. Archivo `.env`

```bash
cp env.example .env
```

Editar `.env` y completar `DATABASE_URL` con el usuario, la clave, el host y la base propios. El archivo `.env` no se versiona.

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Dirección de la base con el driver asincrónico: `postgresql+asyncpg://usuario:clave@host:5432/libreria`. Obligatoria |
| `ECHO_SQL` | Con `true`, muestra en la consola las consultas emitidas. Opcional; por defecto `false` |

### 5. Esquema

El esquema se crea solo con las migraciones de Alembic:

```bash
alembic upgrade head
```

### 6. Datos iniciales

```bash
python seed.py
```

Vacía las tablas, reinicia los identificadores y carga siempre los mismos datos. Se puede correr las veces que haga falta para volver al estado inicial.

### 7. Servidor

```bash
uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000` y la documentación interactiva en `http://127.0.0.1:8000/docs`.

Para comprobar que está en pie:

```bash
curl http://127.0.0.1:8000/health/live    # {"estado":"vivo"}
curl http://127.0.0.1:8000/health/ready   # {"estado":"ok","base":"disponible"}
```

## Casos de prueba

Los casos están en `test/`, como archivos `.http`. Cada caso indica la respuesta esperada en un comentario. Se ejecutan con un cliente que lea ese formato, como la extensión REST Client de Visual Studio Code o el cliente HTTP de los IDE de JetBrains.

Antes de ejecutarlos, correr `python seed.py`.

| Archivo | Casos |
|---------|-------|
| `test/casos_errores.http` | C-01 a C-05 y C-08: validación, conflictos y búsqueda segura |
| `test/casos_venta.http` | C-06 y C-07: alta de venta y lecturas con cantidad fija de consultas |
| `test/evidencia_c07.md` | Evidencia del caso C-07: fragmento de la consola con las consultas |

Para ver las consultas del caso C-07, arrancar el servidor con el diagnóstico activado:

```bash
ECHO_SQL=true uvicorn app.main:app
```

## Migraciones

```bash
alembic upgrade head     # aplica todas las migraciones
alembic downgrade -1     # deshace la última
alembic current          # muestra la revisión aplicada
```

## Estructura

```
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
test/                    casos de prueba en formato .http
seed.py                  carga del estado inicial
```

Módulos: `health`, `editoriales`, `generos`, `autores`, `libros`, `clientes` y `ventas`.
