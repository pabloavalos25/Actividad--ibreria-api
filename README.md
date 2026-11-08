# Librería API — Parcial Capítulos 1 a 6

API REST asincrónica para catálogo, clientes, ventas atómicas, inventario de sólo agregado y control de acceso con usuarios, roles con vigencia y auditoría. Entrega de **Programación III — UTN**, continuación del TP de capítulos 1 a 4 hasta el capítulo 6 (*Del objeto a la transacción*).

**Integrantes del grupo: Pablo Avalos, Ismael Suarez y Sofia Blangetti.**

**Repositorio:** [github.com/pabloavalos25/Actividad--ibreria-api](https://github.com/pabloavalos25/Actividad--ibreria-api)

## Índice

- [Organización de la entrega](#organización-de-la-entrega)
- [Despliegue en línea](#despliegue-en-línea)
- [Stack y requisitos](#stack-y-requisitos)
- [Puesta en marcha desde cero](#puesta-en-marcha-desde-cero)
- [Variables de entorno](#variables-de-entorno)
- [Estado inicial](#estado-inicial)
- [Modelo de datos](#modelo-de-datos)
- [Migraciones](#migraciones)
- [Endpoints del parcial](#endpoints-del-parcial)
- [Arquitectura y reglas](#arquitectura-y-reglas)
- [Casos C-01 a C-16 y evidencias](#casos-c-01-a-c-16-y-evidencias)
- [Pruebas automatizadas](#pruebas-automatizadas)
- [Estructura](#estructura)
- [Troubleshooting](#troubleshooting)
- [Checklist de entrega](#checklist-de-entrega)
- [Integrantes](#integrantes)

## Organización de la entrega

| Ubicación | Contenido y alcance |
|-----------|--------------------|
| Raíz del repositorio → `parcial/` en el ZIP | Parcial capítulos 1–6: 14 tablas, 4 migraciones, autenticación, RBAC, stock, ventas, seed, casos C-01 a C-16 y evidencias. Este README describe esa aplicación. |
| [`despliegue/`](despliegue/DEPLOY.md) | TP capítulos 1–4 preservado, con 2 migraciones y empaquetado Docker para los ejercicios 9 y 10. **No incluye los usuarios, roles ni movimientos de stock del parcial.** |

El empaquetador `scripts/package_entrega.py` organiza las dos carpetas y excluye entornos virtuales, cachés, `.env`, archivos temporales, Git y artefactos de agentes. No incorporar credenciales reales al repositorio, a la imagen ni al ZIP.

## Despliegue en línea

- **API del TP 1–4:** [https://api.ismaelsuarez.me](https://api.ismaelsuarez.me).
- **Swagger del TP 1–4:** [https://api.ismaelsuarez.me/docs](https://api.ismaelsuarez.me/docs).
- **Método:** VPS **Hostinger**, administrado con **Easypanel**; imagen construida desde el Dockerfile de `despliegue/`. PostgreSQL es un servicio separado en la red interna, con volumen persistente y sin publicar el puerto 5432. El proxy proporciona HTTPS.
- **Alcance:** Ejercicio 10, **sólo el TP de capítulos 1 a 4**, no el parcial ampliado descrito abajo. El parcial se ejecuta localmente siguiendo esta guía.
- **Registro del despliegue:** 2026-11-08, inicio aproximado 20:23 UTC (17:23 Argentina, UTC−3), según la evidencia conservada. El servicio debe mantenerse disponible hasta la publicación de las notas.

Consultar la [guía de despliegue y actualización](despliegue/DEPLOY.md) y la [evidencia real D-01 a D-08](despliegue/evidencia/vps_ejercicio10.md). Esos registros documentan la ejecución observada; no garantizan disponibilidad futura. No volver a ejecutar el seed del VPS para actualizar: reemplaza los datos.

## Stack y requisitos

Se requiere **Python 3.12+** y **PostgreSQL 16+**, con una base de desarrollo vacía creada y accesible. Las dependencias se declaran en [`requirements.txt`](requirements.txt); no se presentan versiones locales como requisitos.

| Componente | Restricción declarada / uso |
|------------|----------------------------|
| FastAPI + Uvicorn | `fastapi[standard]>=0.111`; HTTP, OpenAPI y servidor ASGI |
| SQLModel | `==0.0.24`; tablas y DTO |
| SQLAlchemy asincrónico | `sqlalchemy[asyncio]>=2.0`; sesiones, consultas y transacciones |
| asyncpg | `>=0.30`; driver PostgreSQL |
| Alembic | `>=1.13`; esquema versionado, plantilla asincrónica |
| pydantic-settings | `>=2.0,<3`; configuración tipada |
| python-dotenv | `>=1.0`; soporte de entorno |
| bcrypt | `>=4.0,<6`; hash de contraseñas |
| PyJWT | `>=2.10,<3`; tokens HS256 en cookie |
| Pruebas | `pytest>=8,<10`, `httpx>=0.28,<1` en `requirements-dev.txt` |
| Docker (entregable TP) | Base `python:3.12-alpine`, usuario `app` sin privilegios y HEALTHCHECK local |

## Puesta en marcha desde cero

Esta puesta en marcha (dependencias, configuración, migraciones, seed y servidor) se puede ejecutar en cualquiera de estos contextos:

- **Checkout del repositorio:** trabajar desde su raíz, donde están `app/`, `seed.py` y `despliegue/`.
- **Entrega extraída:** trabajar dentro de `parcial/`, conservando `despliegue/` como carpeta hermana. No hace falta Git para ejecutar la aplicación, los casos `.http` ni las pruebas portables.

Crear previamente una base vacía, por ejemplo `libreria`, con las credenciales propias de PostgreSQL. La suite completa del checkout, el verificador PostgreSQL y la regeneración del ZIP se ejecutan desde el repositorio, como se indica en Pruebas automatizadas y Checklist de entrega.

### Linux / macOS — bash

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Antes de continuar:** completar `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` y, si corresponde, `POSTGRES_PORT` en `.env`. Pegar el valor generado en `JWT_SECRET`. No versionar ese archivo ni compartir sus valores.

```bash
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

### Windows — PowerShell

```powershell
py -3 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item env.example .env
& ./.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Completar `.env` **antes de aplicar las migraciones**, igual que en Linux/macOS. El uso del ejecutable explícito evita depender de la activación de PowerShell.

```powershell
& ./.venv/Scripts/python.exe -m alembic upgrade head
& ./.venv/Scripts/python.exe seed.py
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

> **Atención:** `python seed.py` vacía las 14 tablas del dominio con `TRUNCATE … RESTART IDENTITY CASCADE`. Usarlo sólo en una base de desarrollo cuyos datos se puedan reemplazar, nunca como paso de actualización de una base con datos que deban conservarse.

### Acceso y salud local

- API: `http://127.0.0.1:8000` · Swagger: `http://127.0.0.1:8000/docs`.
- `GET /health/live` → **200**, `{"estado": "vivo"}`; no consulta PostgreSQL.
- `GET /health/ready` → **200**, `{"estado": "ok", "base": "disponible"}`, tras `SELECT 1`; si la base no responde → **503**, `{"detail": "Base de datos no disponible"}`.

## Variables de entorno

[`app/core/config.py`](app/core/config.py) lee el entorno del proceso y `.env` mediante `Settings(BaseSettings)`; el entorno del proceso tiene prioridad. `database_url` se calcula con `URL.create("postgresql+asyncpg", ...)`. **La raíz no usa `DATABASE_URL` como variable de configuración**; esa variable corresponde al TP conservado en `despliegue/`.

| Variable | Uso | Valor por defecto |
|----------|-----|-------------------|
| `POSTGRES_USER` | Usuario PostgreSQL | Obligatoria, sin valor predeterminado |
| `POSTGRES_PASSWORD` | Contraseña PostgreSQL; `SecretStr` | Obligatoria, sin valor predeterminado |
| `POSTGRES_DB` | Base de datos | Obligatoria; `env.example` propone `libreria` |
| `POSTGRES_HOST` | Host PostgreSQL | Obligatoria; `env.example` propone `127.0.0.1` |
| `POSTGRES_PORT` | Puerto (`1..65535`) | `5432` |
| `JWT_SECRET` | Firma/verificación HS256; `SecretStr` | Obligatoria, sin valor predeterminado |
| `SQL_ECHO` | Log de SQL; admite alias `ECHO_SQL` | `false` |
| `DB_POOL_SIZE` | Conexiones base del pool (`>=1`) | `5` |
| `DB_MAX_OVERFLOW` | Conexiones adicionales (`>=0`) | `10` |
| `BCRYPT_ROUNDS` | Factor de costo (`4..31`) | `12` |
| `BCRYPT_CONCURRENCY` | Operaciones bcrypt simultáneas (`>=1`) | `4` |
| `JWT_TTL_SECONDS` | Vigencia del token y `Max-Age` de la cookie (`>=1`) | `1800` |
| `COOKIE_SECURE` | Atributo `Secure` de la cookie; activar bajo HTTPS | `false` |

## Estado inicial

[`seed.py`](seed.py) reinicia los identificadores y carga datos determinísticos después de `alembic upgrade head`. Calcula los hashes antes de iniciar las escrituras; utiliza el costo configurado en `BCRYPT_ROUNDS` al ejecutarse desde la consola.

### Cuentas de demostración

**Contraseña común pública del seed: `secreto123`**. Son cuentas ficticias para la evaluación local, no credenciales de infraestructura.

| ID | Nombre | Email | Rol vigente | Cambio obligatorio | Cliente vinculado |
|----|--------|-------|-------------|--------------------|-------------------|
| 1 | Administrador | `admin@example.com` | `ADMIN` | No | — |
| 2 | Administrador Auxiliar | `admin2@example.com` | `ADMIN` | No | — |
| 3 | Vendedor | `vendedor@example.com` | `VENDEDOR` | No | — |
| 4 | Ana Paz | `ana@example.com` | `CLIENTE` | No | `cliente.id=3` |
| 5 | Vendedor Nuevo | `nuevo@example.com` | `VENDEDOR` | Sí | — |

Iniciar sesión con `POST /auth/login`; el cliente HTTP debe conservar la cookie `access_token`. No se usa `Authorization: Bearer`.

### Catálogo y clientes

Los identificadores siguen el orden de inserción del seed:

- **Editoriales:** 1 Emecé, 2 Sudamericana, 3 Anagrama.
- **Géneros:** 1 Policial, 2 Novela, 3 Cuento.
- **Autores:** 1 Julio Cortázar, 2 Ricardo Piglia, 3 Silvina Ocampo, 4 Adolfo Bioy Casares, 5 Jorge Luis Borges, 6 Alejandra Pizarnik.

| Libro ID | Título | ISBN | Precio | Stock actual | Editorial / género ID | Autoría (en orden) |
|----------|--------|------|--------|--------------|-----------------------|--------------------|
| 1 | Rayuela | `978-950-00-0001-1` | `25000.00` | 10 | 2 / 2 | Cortázar (`autor`) |
| 2 | Antología de la literatura fantástica | `978-950-00-0002-8` | `30000.00` | 5 | 1 / 3 | Borges, Bioy Casares, Ocampo (`coautor`, órdenes 1, 2, 3) |
| 3 | Ficciones | `978-950-00-0003-3` | `22000.00` | 8 | 1 / 3 | Borges (`autor`) |
| 4 | Respiración artificial | `978-950-00-0004-4` | `27000.00` | 3 | 3 / 2 | Piglia (`autor`) |
| 5 | Bestiario | `978-950-00-0005-5` | `19500.00` | 1 | 2 / 3 | Cortázar (`autor`) |

El ISBN `978-950-00-0006-6` queda libre para los casos de alta.

| Cliente ID | Nombre | Email | Perfil / cuenta |
|------------|--------|-------|-----------------|
| 1 | Lucía Fernández | `lucia@example.com` | Con perfil, sin usuario |
| 2 | Tomás Ríos | `tomas@example.com` | Sin perfil ni usuario |
| 3 | Ana Paz | `ana@example.com` | Sin perfil; `usuario_id=4` |

### Venta e inventario

- **Venta 1:** cliente 1, `1 × Rayuela` a `25000.00` y `2 × Ficciones` a `22000.00`; total **`69000.00`**.
- **7 movimientos:** cinco ingresos por libro 1 a 5 (`+11, +5, +10, +3, +1`, usuario 1) y dos egresos de la venta 1 (`−1` del libro 1 y `−2` del libro 3, usuario 3). En cada libro, `stock = SUM(movimiento_stock.cantidad)`.
- **1 evento de seguridad:** actor `SISTEMA`, acción `Carga de los datos iniciales`.

## Modelo de datos

Las **14 tablas de dominio**, declaradas en `app/modules/*/models.py`, son:

| Tabla | Responsabilidad / relaciones principales |
|-------|------------------------------------------|
| `editorial` | Nombre único; una editorial publica muchos libros |
| `genero` | Nombre único; género opcional del libro |
| `autor` | Autorías de libros a través de `libro_autor` |
| `libro` | ISBN, título, precio `NUMERIC(10,2)`, stock, editorial, género y `borrado_en` |
| `libro_autor` | N:M; PK compuesta `(libro_id, autor_id)`, rol y orden `>=1` |
| `cliente` | Email único, vínculo opcional y único a `usuario` |
| `perfil_cliente` | Perfil opcional del cliente; `cliente_id` único (1:1) |
| `venta` | Cliente, fecha con zona horaria y total `NUMERIC(12,2)` |
| `renglon_venta` | Venta, libro, cantidad positiva y precio unitario copiado (`NUMERIC(10,2)`) |
| `usuario` | Email único, hash, activo y cambio obligatorio de contraseña |
| `asignacion_rol` | Usuario, rol, inicio, vencimiento, revocación y otorgante opcional |
| `intento_acceso` | Fecha, email, IP y resultado del login |
| `evento_seguridad` | Fecha, actor y acción auditada |
| `movimiento_stock` | Libro, usuario, venta opcional, cantidad no nula ni cero, motivo y fecha |

`libro_autor.rol` admite `autor`, `coautor`, `traductor` e `ilustrador`. `asignacion_rol.rol` admite `ADMIN`, `VENDEDOR` y `CLIENTE`. El índice `uq_asignacion_rol_abierta` permite a lo sumo una asignación no revocada por `(usuario_id, rol)`. El índice `uq_libro_isbn_vigente` exige ISBN único sólo donde `borrado_en IS NULL`.

## Migraciones

El esquema se crea **exclusivamente con Alembic**, nunca con `create_all`. Cadena lineal en [`migrations/versions/`](migrations/versions/):

| Orden | Revisión | Cambio |
|-------|----------|--------|
| 1 | `846f445b2248` | Esquema inicial del TP sin género |
| 2 | `332ba12e013b` | Tabla `genero`, FK e índice de `libro.genero_id` |
| 3 | `3e5d56535b0e` | Acceso y auditoría, movimientos, vínculo cliente-usuario, baja lógica e ISBN único parcial |
| 4 | `a05a50bc58a8` | Función `impedir_cambio_movimiento_stock()` y trigger `trg_movimiento_stock_solo_agregado`, escritos a mano |

`alembic upgrade head` aplica la cadena y `alembic current` muestra la revisión aplicada. El trigger rechaza `UPDATE` y `DELETE` por fila con **SQLSTATE 23514**; permite `INSERT`. El ciclo de reversión se prueba sólo sobre un cluster nuevo aislado, no sobre la base de trabajo.

## Endpoints del parcial

Rutas de `app/modules/*/router.py`, montadas en [`app/main.py`](app/main.py). La documentación interactiva local está en `/docs`.

**Permisos:** Público = sin sesión; Sesión = usuario activo autenticado; Personal = `ADMIN` o `VENDEDOR`; Propietario = usuario vinculado al cliente de la venta. Los roles se consultan en la base en cada petición.

**Códigos comunes:** todas las rutas protegidas pueden responder **401** por sesión ausente/inválida/vencida y **403** por cambio de contraseña pendiente. Las que exigen rol pueden responder **403** por falta de permiso. `/auth/yo` y `/auth/cambiar-password` requieren sesión pero permiten el cambio pendiente. Los errores de entrada, IDs y paginación se traducen a **422**; los conflictos de integridad, a **409** con mensaje propio. Las tablas indican éxito y errores específicos adicionales, no fallos de infraestructura.

### Salud y autenticación

| Método | Ruta | Permiso | Éxito | Errores relevantes |
|--------|------|---------|-------|--------------------|
| GET | `/health/live` | Público | 200 | — |
| GET | `/health/ready` | Público | 200 | 503 base no disponible |
| POST | `/auth/registro` | Público | 201 | 409 email ocupado en usuario o cliente; 422 |
| POST | `/auth/login` | Público | 200 + cookie | 401 credenciales; 429 límite de intentos; 422 |
| POST | `/auth/logout` | Público | 200, borra cookie | — |
| GET | `/auth/yo` | Sesión | 200 | 401 |
| POST | `/auth/cambiar-password` | Sesión | 200 | 401 contraseña actual/sesión; 422 |

### Usuarios, roles y auditoría

| Método | Ruta | Permiso | Éxito | Errores relevantes |
|--------|------|---------|-------|--------------------|
| POST | `/usuarios` | ADMIN | 201 | 409 email ocupado; 422 |
| GET | `/usuarios/{usuario_id}/roles` | ADMIN | 200, lista de historial | 404 usuario; 422 |
| POST | `/usuarios/{usuario_id}/roles` | ADMIN | 201 | 404 usuario; 409 rol ya asignado; 422 vencimiento/entrada |
| DELETE | `/usuarios/{usuario_id}/roles/{rol}` | ADMIN | 200 | 404 usuario/asignación; 409 autoprotección ADMIN; 422 |
| GET | `/eventos` | ADMIN | 200 paginado | 422 |

### Catálogo e inventario

| Método | Ruta | Permiso | Éxito | Errores relevantes |
|--------|------|---------|-------|--------------------|
| POST | `/editoriales/` | ADMIN | 201 | 409 nombre repetido; 422 |
| GET | `/editoriales/` | Público | 200 paginado | 422 |
| GET | `/editoriales/{editorial_id}` | Público | 200 | 404; 422 |
| PATCH | `/editoriales/{editorial_id}` | ADMIN | 200 | 404; 409; 422 |
| GET | `/editoriales/{editorial_id}/libros` | Público | 200 paginado | 404; 422 |
| POST | `/generos/` | ADMIN | 201 | 409 nombre repetido; 422 |
| GET | `/generos/` | Público | 200 paginado | 422 |
| GET | `/generos/{genero_id}/libros` | Público | 200 paginado | 404; 422 |
| POST | `/autores/` | ADMIN | 201 | 422 |
| GET | `/autores/{autor_id}` | Público | 200 | 404; 422 |
| PATCH | `/autores/{autor_id}` | ADMIN | 200 | 404; 422 |
| GET | `/autores/{autor_id}/libros` | Público | 200 paginado | 404; 422 |
| POST | `/libros/` | ADMIN | 201 | 409 ISBN vigente/FK/autoría; 422 |
| GET | `/libros/` | Público | 200 paginado | 422 |
| GET | `/libros/{libro_id}` | Público | 200 | 404 no vigente/inexistente; 422 |
| PATCH | `/libros/{libro_id}` | ADMIN | 200 | 404; 422 (incluye intento de editar stock) |
| DELETE | `/libros/{libro_id}` | ADMIN | 204 | 404; 422 |
| POST | `/libros/{libro_id}/reponer` | ADMIN | 200, detalle actualizado | 404 inexistente; 409 dado de baja; 422 |
| GET | `/libros/{libro_id}/movimientos` | ADMIN | 200 paginado | 404 inexistente; 422 |

### Clientes y ventas

| Método | Ruta | Permiso | Éxito | Errores relevantes |
|--------|------|---------|-------|--------------------|
| POST | `/clientes/` | Personal | 201 | 409 email repetido; 422 |
| GET | `/clientes/{cliente_id}` | Personal | 200 | 404; 422 |
| PATCH | `/clientes/{cliente_id}` | Personal | 200 | 404; 409; 422 |
| POST | `/clientes/{cliente_id}/perfil` | Personal | 201 | 404; 409 perfil ya existente; 422 |
| GET | `/clientes/{cliente_id}/ventas` | Personal | 200 paginado | 404; 422 |
| POST | `/ventas/` | Personal | 201 | 409 cliente/libro no disponible/stock insuficiente; 422 |
| GET | `/ventas/` | Personal | 200 paginado | 422 |
| GET | `/ventas/{venta_id}` | Personal o propietario, con sesión | 200 | 403 venta ajena; 404; 422 |
| GET | `/mis-ventas` | Sesión (sólo compras propias) | 200 paginado | 422 |

**Paginación:** los endpoints marcados como paginados devuelven `{items, total, page, size, pages}`; `page>=1`, `size=1..100` (por defecto `20`), `pages=max(1, ceil(total/size))`. Pedir una página superior a `pages` da 422. El historial `/usuarios/{usuario_id}/roles` devuelve una lista, no una página.

**Filtros y límites del contrato:** `GET /libros/?titulo=ficc&genero_id=3&page=1&size=20` combina título sin distinguir mayúsculas y género mediante parámetros ligados. `PATCH /libros/{libro_id}` sólo admite `titulo` y `precio`. No hay listado general de autores/clientes, detalle individual de género ni modificación de ventas. Los movimientos también se pueden consultar para un libro dado de baja.

## Arquitectura y reglas

- **Capas:** `Router → Service → UnitOfWork → Repository → Model`. Las dependencias construyen los UoW con la sesión de la petición; los servicios no crean sesiones. Los repositorios hacen `flush`, no `commit`; el UoW confirma o revierte y la dependencia cierra la sesión.
- **Contratos y dinero:** DTO de entrada con `extra="forbid"`; dinero con `Decimal`/`NUMERIC`, nunca `float`. Los errores `IntegrityError` y `DataError` se traducen a 409/422 sin exponer texto interno de PostgreSQL.
- **Acceso:** bcrypt se ejecuta con `asyncio.to_thread` bajo semáforo; las contraseñas admiten como máximo 72 bytes UTF-8. El login usa hash ficticio precalculado para correos inexistentes y el mismo mensaje 401. Tras cinco fallos del mismo `(email, ip)` en 60 segundos, el siguiente intento devuelve 429 con `Retry-After`, sin ejecutar bcrypt. Un login correcto reinicia el conteo sin borrar el historial.
- **Sesión y autorización:** JWT HS256 sólo en cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable), nunca en el cuerpo ni por Bearer. Los roles del token son informativos; `/auth/yo` muestra `roles_vigentes` y `roles_token`. El cambio pendiente bloquea el grupo protegido, no las lecturas públicas ni las rutas `/auth`.
- **Atomicidad y auditoría:** registro crea usuario + rol CLIENTE + cliente en una transacción; no se apropia de clientes previos. Alta de personal, cambios de rol y contraseña generan eventos en su misma transacción. `intento_acceso` usa una sesión/transacción independiente para persistir incluso si el login revierte. No se permite revocar el propio ADMIN ni dejar al sistema sin administradores vigentes.
- **Stock y venta:** alta con `stock_inicial`, reposición y venta pasan por `modificar_stock`. Una venta exige renglones no vacíos, libros sin repetir y cantidades positivas; copia precios y calcula el total. Venta, renglones, descuentos y movimientos se confirman juntos o se revierten juntos. El trigger protege el carácter de sólo agregado de los movimientos.
- **Baja lógica:** `DELETE` marca `borrado_en`; el libro desaparece del catálogo y no se puede vender ni reponer. El ISBN queda disponible para un nuevo libro vigente y las ventas históricas conservan acceso al libro original.
- **Lecturas y tareas:** precarga con `joinedload`/`selectinload`, sin consultas por cada renglón. Tras confirmar una venta, `BackgroundTasks` espera cooperativamente `asyncio.sleep(0.5)` y registra el comprobante en consola; **no envía correo real**.

Más detalle en [persistencia](docs/PERSISTENCIA.md), [requisitos](docs/REQUISITOS_PARCIAL_CAP1A6.md) y [progreso verificado](docs/PROGRESO_PARCIAL_CAP1A6.md).

## Casos C-01 a C-16 y evidencias

Desde la raíz del checkout o desde `parcial/` de la entrega extraída, usar **REST Client de VS Code** o el cliente HTTP de JetBrains con el servidor local en ejecución. Restaurar con `python seed.py` **antes de cada colección completa**, no entre sus bloques: las peticiones de una colección dependen de las anteriores. Los login usan `# @name` y `# @no-cookie-jar` para mantener sesiones separadas y enviar cada cookie explícitamente.

- **Acceso (A):** [`test/casos_acceso_autorizacion.http`](test/casos_acceso_autorizacion.http).
- **Ventas, stock y catálogo (V):** [`test/casos_ventas_stock_catalogo.http`](test/casos_ventas_stock_catalogo.http).

| Caso | Colección | Qué verificar |
|------|-----------|---------------|
| **C-01** | A | `/libros/abc` → 422 antes del handler |
| **C-02** | A | Registro 201; colisión en usuario o cliente → 409 sin filas sueltas |
| **C-03** | A | Login con cookie y cuerpo sin token; sin cookie o sólo Bearer → 401 |
| **C-04** | A | Correo existente con clave mala e inexistente → mismo 401; comparar tiempos |
| **C-05** | A | Cinco fallos 401; sexto intento dentro de 60 s → 429 con `Retry-After` |
| **C-06** | A | Sin sesión 401; vendedor creando libro 403; cliente ve venta propia 200 y ajena 403 |
| **C-07** | A | Revocación afecta la sesión abierta; historial conserva la fila; vencimiento pasado/sin zona → 422 |
| **C-08** | A | Intento de revocar el propio ADMIN → 409 |
| **C-09** | A | Cambio pendiente → 403 en protegidas; cambiar contraseña permite continuar con la misma cookie |
| **C-10** | V | Venta de libros 2 y 4 → 201, total `57000.00`, descuentos, movimientos y comprobante posterior |
| **C-11** | V | Stock insuficiente de Bestiario → 409 sin venta ni descuentos parciales; Rayuela sigue en 10 |
| **C-12** | V | Cliente inexistente, libro inexistente o dado de baja → 409 sin escrituras parciales |
| **C-13** | V | Reposición 200, baja 204, venta/reposición de baja 409, ISBN reutilizable 201 y duplicado vigente 409; venta histórica legible |
| **C-14** | SQL + V | PostgreSQL rechaza UPDATE/DELETE de movimientos con SQLSTATE 23514 y conserva la fila |
| **C-15** | V | Detalles con 2 y 4 renglones mantienen cantidad fija de SELECT, con `SQL_ECHO=true` |
| **C-16** | V | Búsqueda ligada sin inyección; filtro y paginación; página fuera de rango/tamaño 500 → 422; PATCH precio 200 y stock 422 |

Evidencias complementarias:

- C-10: [`evidencia/ej8_comprobante.md`](evidencia/ej8_comprobante.md).
- C-14: [`test/solo_agregado.sql`](test/solo_agregado.sql), [`evidencia/ej7_integridad.md`](evidencia/ej7_integridad.md) y [`evidencia/c14_psql.txt`](evidencia/c14_psql.txt).
- C-15: [`evidencia/ej8_lecturas.md`](evidencia/ej8_lecturas.md): 2 SELECT de repositorio y 4 por petición autenticada, tanto con 2 como con 4 renglones; no es un conteo universal para todas las rutas.

Para C-14, sobre la base local de desarrollo confirmada y después del seed (movimiento 1 existente), adaptar host/usuario/base a la configuración propia, sin escribir contraseñas en el comando:

```bash
psql -X --no-password -h 127.0.0.1 -p 5432 -U postgres -d libreria \
  -v movimiento_id=1 -f test/solo_agregado.sql
```

El SQL verifica ambos rechazos, compara la fila y termina con rollback. Si la conexión requiere contraseña, usar la configuración segura propia de `psql`.

## Pruebas automatizadas

### Desde el checkout del repositorio

Ejecutar desde la **raíz del repositorio**, con el entorno virtual activo, `despliegue/` dentro de esa raíz y Git disponible con el historial del proyecto. Así se ejecuta la suite completa, incluidas las pruebas de procedencia del TP y del empaquetador:

```bash
pip install -r requirements-dev.txt
python -m pytest -q test/test_readme_parcial.py
python -m pytest -q
```

`pytest.ini` selecciona `test/` para la suite predeterminada. Las pruebas integradas de PostgreSQL están separadas en `postgres_tests/`; no quedan cubiertas por el comando anterior.

**También desde la raíz del checkout**, el verificador siguiente requiere binarios PostgreSQL locales: crea un **cluster nuevo aislado** en `tmp/`, no usa el `.env` de trabajo, comprueba `upgrade head → check → downgrade base → upgrade head → check`, ejecuta `postgres_tests/` y detiene su servidor al terminar:

```bash
python scripts/test_postgres.py --pg-bin "<directorio-de-binarios-PostgreSQL>"
```

Reemplazar el marcador por el directorio que contiene `initdb` y `pg_ctl`. En Windows, el runner usa por defecto `C:/Program Files/PostgreSQL/17/bin` si se omite `--pg-bin`. Los logs se conservan en el directorio temporal de cada ejecución. Las evidencias de Docker/VPS se consultan por separado en `despliegue/`.

### Desde la entrega extraída

Dentro de **`parcial/`**, con `despliegue/` como carpeta hermana y el entorno virtual de la puesta en marcha activo:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Se ejecutan las pruebas portables; las que necesitan el checkout Git o el empaquetador se **omiten con un motivo explícito**. Las pruebas del TP usan `despliegue/` hermano. Estas omisiones no equivalen a validar el empaquetado ni la procedencia contra el historial: para eso se usa la suite completa del repositorio. No regenerar el ZIP desde `parcial/` extraído.

## Estructura

```text
app/
├── main.py                 lifespan y grupos de rutas públicas/protegidas
├── core/                   configuración, sesión, seguridad, permisos, UoW y paginación
└── modules/
    ├── health/             liveness y readiness
    └── autores, clientes, editoriales, generos, libros, usuarios, ventas/
        ├── models.py       tablas, relaciones e índices
        ├── schemas.py      DTO de entrada/salida
        ├── router.py       rutas y permisos
        ├── service.py      casos de uso
        ├── repository.py   persistencia y precarga
        └── unit_of_work.py repositorios por operación y dependencia de sesión
migrations/versions/        cuatro revisiones del parcial
seed.py                     estado inicial reproducible
.env                        configuración privada local; no se entrega
env.example                 plantilla pública sin secretos
requirements*.txt           dependencias de aplicación y pruebas
test/                       pruebas, dos colecciones .http y solo_agregado.sql
postgres_tests/             integración sobre PostgreSQL real aislado
evidencia/                  integridad, consultas y asincronía del parcial
scripts/                    verificadores y empaquetador
docs/                       consigna y documentación técnica
despliegue/                 TP 1–4, Docker, DEPLOY.md y evidencia D-01 a D-08
```

## Troubleshooting

| Síntoma | Comprobación / solución |
|---------|-------------------------|
| Faltan variables al arrancar | Ejecutar desde la raíz del checkout o desde `parcial/` extraído; completar todas las obligatorias en `.env`. Revisar si el entorno del proceso está sobrescribiendo el archivo. |
| `/health/live` da 200 pero `/health/ready` da 503 | Revisar PostgreSQL, host/puerto y credenciales. Live no prueba la conexión a la base. |
| Error de esquema o revisión | Revisar `alembic current` y aplicar `alembic upgrade head` sobre la base correcta antes del seed. No usar `create_all`. |
| 401 tras login | Conservar/enviar cookie `access_token`; no Bearer. Para HTTP local, dejar `COOKIE_SECURE=false`; activar en HTTPS. |
| 403 con `nuevo@example.com` | Ejecutar `POST /auth/cambiar-password` con su cookie; las rutas protegidas exigen resolver el cambio pendiente. |
| 429 al repetir pruebas de acceso | Respetar `Retry-After`; el límite cuenta por email/IP en una ventana de 60 segundos. |
| No se ven SELECT en C-15 | Activar `SQL_ECHO=true` en el proceso o `.env` y reiniciar el servidor. |
| PowerShell no activa `.venv` | Usar directamente `& ./.venv/Scripts/python.exe -m ...`, como en la puesta en marcha. |
| Puerto 8000 ocupado | Usar `uvicorn app.main:app --reload --port 8001` y ajustar la URL del cliente HTTP. |

## Checklist de entrega

- [ ] Instalar dependencias y completar el entorno privado en una base de desarrollo vacía.
- [ ] Aplicar las cuatro migraciones y cargar el seed; comprobar cuentas, catálogo y stock inicial.
- [ ] Obtener 200 en live/ready y abrir `/docs` local.
- [ ] Ejecutar C-01 a C-16 restaurando el seed entre colecciones completas; conservar evidencias SQL, consultas y comprobante.
- [ ] Desde la raíz del checkout: ejecutar la suite completa y la integración PostgreSQL aislada con `scripts/test_postgres.py`.
- [ ] Desde `parcial/` extraído, con `despliegue/` hermano: comprobar puesta en marcha, casos `.http` y `python -m pytest -q` (omisiones justificadas de pruebas exclusivas del checkout).
- [ ] Confirmar URL pública del **TP 1–4**, guía y evidencia D-01 a D-08; mantener el servicio hasta las notas.
- [ ] **Sólo desde la raíz del checkout completo**, con `despliegue/` y Git disponibles: regenerar y verificar el ZIP de la versión final integrada con `python scripts/package_entrega.py` (responsabilidad de cierre de entrega; no ejecutar desde `parcial/` extraído).
- [ ] Revisar que el ZIP tenga `parcial/` y `despliegue/`, sin `.env`, credenciales, entornos virtuales ni cachés.
- [ ] Confirmar integrantes y subir el archivo final al campus.

## Integrantes

**Trabajo grupal — Programación III, UTN. Parcial capítulos 1 a 6.**

![Pablo Avalos](https://img.shields.io/badge/Pablo_Avalos-UTN-1976D2?style=for-the-badge)
![Ismael Suarez](https://img.shields.io/badge/Ismael_Suarez-UTN-388E3C?style=for-the-badge)
![Sofia Blangetti](https://img.shields.io/badge/Sofia_Blangetti-UTN-7B1FA2?style=for-the-badge)
