# Progreso del parcial

Actualizado: 5 de noviembre de 2026. Fuente de requisitos: `Parcial_Cap1a6_Consigna.pdf`; matriz completa en [REQUISITOS_PARCIAL_CAP1A6.md](REQUISITOS_PARCIAL_CAP1A6.md). Configuración y seguridad autorizadas expresamente por el usuario en esta sesión; ver [plan](PLAN_PARCIAL_CAP1A6.md).

Estado actual: **ejercicios 1 a 5 implementados**; las secciones cronológicas conservan los resultados de cada bloque. Conteos actuales: **213 pruebas sin DB y 71 online PostgreSQL**, sin casos omitidos dentro de las suites ejecutadas. Sigue el ejercicio 6 (repositorios/UoW y stock).

## Bloque 1 implementado

- TP original preservado en `despliegue/` a partir del commit `54c7fa2e362904999e07857636bb97f087877341`, sin `.env`, `.venv` ni `.git`. Su procedencia está documentada. Se mantiene la raíz como parcial para evitar mover archivos durante el desarrollo; se empaquetará como `parcial/` al entregar.
- Entorno aislado `.venv` operativo, con Python 3.13.12, FastAPI 0.162.0, SQLModel 0.0.24, SQLAlchemy 2.0.57, pydantic-settings 2.16.2, bcrypt 5.0.0 y pytest 9.2.0. Verificados ejecutable y prefix locales. El Python embebido de pgAdmin carece de `venv`; se usó virtualenv temporal, sin instalar paquetes globales. Descargas autorizadas fuera del sandbox; se restauró herencia de permisos únicamente en `.venv/Lib/site-packages` para permitir imports del sandbox.
- `Settings` con variables PostgreSQL separadas, URL calculada con escape correcto, secretos obligatorios y configuración de pool/bcrypt. `migrations/env.py` usa la misma configuración. El seed sigue usando `get_settings` y la fábrica compatibles, pero aún no tiene los datos nuevos del parcial.
- Lifespan crea recursos sin conectar, configura pool, prepara semáforo y hash ficticio una vez, y libera motor en `finally` incluso ante errores de inicialización o ejecución.
- Hash bcrypt fuera del bucle mediante `to_thread`, costo configurable y límite de concurrencia que conserva el cupo hasta finalizar el hilo aun si la coroutine se cancela repetidamente.
- Health y sesiones conservan su comportamiento comprobado: live sin DB, ready con SELECT 1 y 503 propio, sesión por petición con cierre y sin expiración al commit.

## Decisiones del bloque

Los nombres `JWT_SECRET`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `BCRYPT_ROUNDS` y `BCRYPT_CONCURRENCY` son elecciones del proyecto: la consigna no fija esos nombres ni sus valores. Se eligen defaults no secretos 5/10 para pool y 12/4 para bcrypt; están expuestos en `env.example`. Los tests reducen bcrypt a costo 4/5 sin cambiar el default de ejecución.

Se mantiene `ECHO_SQL` como alias de compatibilidad y se documenta `SQL_ECHO` como nombre principal. Settings ignora claves ajenas del archivo de entorno, pero **no utiliza DATABASE_URL como reemplazo de POSTGRES_***: sin los secretos obligatorios no arranca. No se registran Settings ni la URL calculada.

`env.example` tiene contraseña y clave JWT vacías. El `.env` real no se modificó. Para arrancar el parcial hay que completar manualmente las nuevas variables según README.

## TDD Cycle Evidence

No existía suite automatizada: únicamente archivos HTTP del TP. Antes de cambiar producción se agregaron y ejecutaron 7 caracterizaciones, todas verdes. Los casos HTTP que requieren PostgreSQL no se ejecutaron en este bloque.

| Tarea | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Configuración Settings | `test/test_config.py` | Unidad | 7/7 caracterizaciones | TypeError por Settings antigua sin `_env_file` | Confirmado | 14 casos: URL, secretos ausentes/vacíos, rangos, defaults, archivo/entorno | Suite verde; sin refactor de producción adicional |
| Pool configurable | `test/test_database.py` | Integración sin conexión | 21/21 | TypeError por `pool_size` inexistente | Confirmado | 2 configuraciones de pool | Suite verde; sin refactor adicional |
| Hash ficticio bcrypt | `test/test_security.py` | Unidad + bcrypt real | 23/23 | Módulo `app.core.security` inexistente | Confirmado | 2 contraseñas/costos y 2 límites de concurrencia | Suite verde; sin refactor adicional |
| Lifespan | `test/test_lifespan.py` | Integración ASGI + unidad | 27/27 | Hash/función no existentes en lifespan | Confirmado | 5 casos: arranque/pool, fallo hash/petición y 2 secretos ausentes | Limpieza centralizada en finally; suite verde |
| Configuración Alembic | `test/test_migration_config.py` | Subproceso CLI offline | 30/30 antes de editar env.py | Configuración vieja exige DATABASE_URL | Confirmado | 2 casos: SQL generado y JWT ausente | Suite verde; sin refactor adicional |
| Cancelación bcrypt | `test/test_security.py` | Unidad concurrente | 32/32 | Segundo hash entraba mientras seguía el hilo cancelado | Confirmado | 2 casos: cancelación simple y doble | Suite verde; mantiene semáforo hasta terminar worker |
| Health/sesiones existentes | `test/test_core_baseline.py` | ASGI + unidad | 7/7 inicial | No se cambió comportamiento | Confirmado | Live, ready disponible/caída, sesiones normal/error, fábrica/lifespan | Se conservan verdes |

Los números Safety Net reflejan las ejecuciones previas a cada modificación, no una dependencia entre ejercicios. Se corrigieron dos aserciones del propio test que buscaban una cadena vacía dentro del error; no fue un defecto de producción. El temporal global de pytest no era accesible, por lo que `pytest.ini` fija `tmp/pytest` dentro del proyecto.

## Verificación y alcance del bloque 1 (histórico)

Comando principal: `& ./.venv/Scripts/python.exe -m pytest -q` → **36 passed**. Incluye generación SQL offline real de las migraciones existentes con contraseña ficticia con caracteres especiales, en un subproceso con directorio temporal y sin lectura del `.env` real.

Verificación final: suite 36/36 en 2.90 s; revisión independiente 36/36 en 2.87 s. `python -m pip check`: sin dependencias rotas. Importar `seed` y `app.main` funciona sin ejecutar la carga de datos. `git diff --check`: sin errores de espacios (solo avisos normales LF/CRLF). Los 55 archivos extraídos en `despliegue/` coinciden byte por byte con el archivo generado por `git archive`; únicamente se agregó `PROCEDENCIA.md`.

Durante el bloque 1 no se conectó a PostgreSQL, no se ejecutó seed, no se aplicaron migraciones online y no se desplegó al VPS. La verificación online de migraciones se realizó después, en el bloque 2 documentado abajo. Los casos C nuevos y los casos D completos siguen pendientes. El helper bcrypt no incorpora todavía endpoints, emisión/verificación JWT ni autorización.

## Bloque 2 — modelos, relaciones y migraciones

Implementado tras el pedido «Sigamos», manteniendo la autorización de configuración/seguridad ya otorgada.

- Nuevos modelos `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` y `MovimientoStock`, en los módulos exigidos. Las nuevas fechas son `timestamptz`, con defaults UTC cuando corresponde. Intentos y eventos no tienen relaciones ni FK.
- `Cliente.usuario_id` es nullable, UNIQUE e indexado; `Cliente.usuario` y su reversa `Usuario.cliente` son escalares opcionales. Se conserva la unicidad de email.
- Libro conserva precio Decimal, CHECK precio/stock y todas sus relaciones; agrega `borrado_en` y el índice único parcial de ISBN vigente, reemplazando el UNIQUE común.
- Asignaciones tienen CHECK de roles e índice único parcial de usuario/rol no revocado. Un rol vencido aún abierto sigue bloqueando otro hasta revocarlo. `otorgada_por` se interpreta como FK opcional al usuario otorgante, decisión coherente con su significado y documentada aquí; se diferencia del titular con `foreign_keys` en ambos extremos. Todas las nuevas FK están indexadas. No se agregaron CHECK de fechas ni reglas adicionales ajenas a la consigna.
- Movimientos permiten cantidades positivas y negativas, rechazan cero y tienen navegación bilateral con libro, usuario y venta opcional. Las relaciones de historial no borran movimientos ni asignaciones en cascada.
- Revisión **3e5d56535b0e** realmente generada con `alembic revision --autogenerate -m acceso_y_movimientos_stock`, contra un PostgreSQL 17 aislado con las dos migraciones del TP. Se leyó antes de aplicar y se dejó comentario de revisión. Correcciones necesarias: AutoString sin import del generador se cambió por `sa.String` equivalente; se nombró la FK de cliente para corregir `drop_constraint(None)` del downgrade. Se verificó drop del UNIQUE ISBN anterior y creación del parcial con predicado real.
- Revisión **a05a50bc58a8**, escrita a mano: función y trigger BEFORE UPDATE/DELETE que rechazan cambios incluso por SQL directo (SQLSTATE 23514). INSERT continúa permitido. Downgrade elimina primero trigger y luego función. Comentario documenta revisión previa.
- Se registraron explícitamente todos los modelos en `migrations/env.py`. `import app.main, seed; configure_mappers()` pasó en proceso fresco, sin ejecutar seed.

### TDD Cycle Evidence — ejercicio 2

| Tarea | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Grafo de modelos y relaciones | `test/test_models.py` | Unidad ORM | 36/36 inicial | ImportError: MovimientoStock inexistente | 8/8 | 2 vínculos cliente, 2 roles, movimientos con/sin venta y 2 intentos | Optional en relaciones, 44/44 verdes |
| Revisión 3, restricciones e índices parciales | `postgres_tests/test_constraints.py` | PostgreSQL real | Esquema TP online y alembic check sin drift | 12 fallos por tablas/columnas nuevas ausentes | Confirmado tras migración autogenerada revisada | 23 casos finales: unicidad/FK/CHECK/ISBN y fechas con 2 offsets | Sin cambio de comportamiento; suite verde |
| Trigger de sólo agregado | `postgres_tests/test_append_only.py` | SQL directo PostgreSQL | 12/12 online previos | 4 fallos: UPDATE/DELETE no eran rechazados | 4/4 | UPDATE y DELETE, cada uno con movimiento positivo/negativo | Suite verde |
| Persistencia y navegación histórica | `postgres_tests/test_relationships.py` | ORM + PostgreSQL real | Restricciones/trigger verdes | Cubiertos por RED del modelo/esquema anterior | 2/2 | Con venta y sin venta; lectura precargada tras baja del libro | Sin refactor adicional |

En los tests de apoyo se corrigieron dos errores de fixture antes de confirmar RED de esquema: `force_rollback` no es argumento de asyncpg.Transaction; se reemplazó por start/rollback explícitos. La editorial de prueba también necesitaba el `pais` obligatorio del TP. No se cambiaron restricciones de producción para hacer pasar fixtures.

### Verificación online reproducible

Se creó un cluster **propio** dentro de `tmp/postgres-ej2/data`, ligado exclusivamente a `127.0.0.1:10628`, con usuario/base de pruebas y sin utilizar credenciales del `.env`. Antes de usarlo se comprobó `SHOW data_directory`. La base `parcial_ej2` recibió las dos revisiones previas como baseline; autogenerate detectó sólo los cambios esperados.

Resultados coordinados después del ciclo completo `head → base → head`:

- Suite sin DB: **44 passed in 5.35s**. Revisión independiente: **44 passed in 6.40s**.
- Suite PostgreSQL: **29 passed in 2.69s**. Revisión independiente: **29 passed in 2.58s**.
- `alembic check`: **No new upgrade operations detected**, antes y después del ciclo.
- Las pruebas ejercitan en la base el ISBN reciclado, rechazo de reactivación conflictiva, roles abiertos/vencidos/revocados, las seis nuevas FK, checks originales, fechas con zona, persistencia y lectura de relaciones y rechazo de UPDATE/DELETE aun si UPDATE no cambia el valor.

`scripts/test_postgres.py` repite desde cero la creación de un cluster nuevo en `tmp/`, usa puerto libre distinto de 5432, verifica ownership/directorio, ejecuta `upgrade head → check → downgrade base → upgrade head → check`, valida que base no deje tablas de dominio ni función del trigger, ejecuta las 29 pruebas online y apaga sólo su propio servidor en `finally`. No acepta URLs o datos de un cluster existente. Las suites online requieren configuración explícita y fallan si falta o no hay conexión; no hacen skip.

El fresh-run final verificado creó `tmp/postgres-tests-5f79da9ca16f`, puerto **52783**: cuatro revisiones desde base vacía, downgrade sin tablas/función remanentes, nuevo upgrade, comparación sin drift, **29 passed in 2.22s**, y **server stopped** al terminar. Los logs completos quedan en `verification.log` y `server.log` de esa carpeta ignorada. Hubo un aviso de permisos de caché pytest; el runner ahora dirige también su caché a su propio temporal.

Particularidades de esta sesión Windows/Codex: initdb no pudo ejecutarse con el token restringido del sandbox, por lo que initdb/pg_ctl requirieron escalación explícita. El launcher `.venv` elevado tuvo un fallo nativo al importar asyncpg; se usó el Python base de pgAdmin con **lectura** de dependencias `.venv/Lib/site-packages` mediante sys.path, sin modificar el entorno global. Cada hijo del runner recibe ese bootstrap porque el Python embebido ignora PYTHONPATH. Comando exacto equivalente reproducible en README. El primer intento del runner quedó esperando un PIPE heredado por el servidor; se detuvo su cluster de puerto33873 y se corrigió a logs de archivo. No se reutilizó ese cluster para fingir éxito.

Los clusters propios de puertos **10628, 33873 y 52783 quedaron detenidos**. Los datos temporales y logs se conservan ignorados en `tmp/`; no se eliminó ni modificó ningún servicio, directorio de datos o base ajenos al task. `despliegue/` y el `.env` real no se modificaron; no se ejecutó seed. La evidencia ampliada está en [ej2_migraciones.md](../evidencia/ej2_migraciones.md).

Cierre verificado: `pg_ctl status` devolvió **no server running** para las tres rutas propias; `git diff --check` no informó errores (sólo avisos LF/CRLF); los 55 archivos del TP preservado siguen sin cambios respecto del archivo de `git archive` original.

El downgrade restaura el UNIQUE global de ISBN del TP: si se intentara bajar sobre datos que ya reutilizaron ISBN, habría que resolver ese conflicto antes. El ciclo exigido se verificó sobre la base de pruebas limpia, sin inventar una política de borrado de datos.

## Siguiente bloque

Ejercicio 3: contratos estrictos, respuestas y paginación. Coordinar sus escrituras con los próximos repositorios/UoW y acceso/stock, sin anticipar autenticación ni lógica de negocio en el bloque de modelos. Seguir el plan; autorizaciones HIGH/CRITICAL ya otorgadas no deben solicitarse de nuevo para el mismo alcance.

Quedan pendientes repositorios/UoW, contratos/paginación, autenticación y autorización completas, stock/ventas atómicas, seed nuevo, archivos HTTP C-01 a C-16, evidencias C-14/C-15 y Docker/VPS D-01 a D-08. El CLI y skills OpenSpec no están disponibles; no se inventó estado ni estructura OPSX.

## Documentación consultada

- Context7: pydantic-settings (BaseSettings, SettingsConfigDict), FastAPI (lifespan/TestClient), SQLAlchemy (URL.create, pool, sesiones asincrónicas).
- [bcrypt oficial](https://github.com/pyca/bcrypt): hashpw, gensalt y costo configurable.


## Ejercicio 3 - contratos, CRUD y paginación (5 de noviembre de 2026)

**Estado:** contratos y listados actuales implementados y verificados. La integración del alta con acceso y el contrato de registro de usuarios quedan pendientes del ejercicio 4; no se declara cerrado el parcial ni el criterio transversal de registro. Gobernanza MEDIUM, sin UI (`Decision: no (no UI)`). No se modificaron `.env`, `despliegue/`, migraciones ni servicios PostgreSQL ajenos.

- DTO separados de tablas; `extra="forbid"` en entradas, límites de longitud/precisión de columnas e IDs/cantidades enteros dentro del rango PostgreSQL. PATCH omite campos no enviados y rechaza null en campos obligatorios. Libro actualiza sólo título/precio y no recibe stock.
- Los ocho listados existentes (`libros`, `editoriales`, `generos`, `ventas`, libros por autor/editorial/género y ventas por cliente) responden `{items,total,page,size,pages}`. `page>=1`, `size=1..100`, default 20, vacío pages=1 y fuera de rango 422. Conteo y elementos parten de la misma consulta filtrada. La búsqueda ilike usa parámetros ligados, verificada también con texto de intento de inyección.
- Alta usa `stock_inicial`; un valor positivo crea `MovimientoStock` con motivo `Stock inicial`, actor real y libro en la misma transacción. Con cero no se crea movimiento (CHECK cantidad<>0). Un conflicto de ISBN o FK revierte libro y movimiento. No se crean usuarios ni actores artificiales.
- `POST /libros/` queda temporalmente protegido por `requerir_usuario_id` que falla cerrado con 401 para cualquier petición, hasta cablear cookie/usuario/roles en ejercicio 4. Un override de pruebas con usuario real permitió verificar el 201 y sus escrituras. No aceptar IDs arbitrarios del cliente al completar esa dependencia.
- Baja lógica 204; recurso inexistente o ya borrado 404. Catálogo y listados por relaciones excluyen borrados. Venta nueva con libro borrado 409; detalle histórico conserva la relación y sus datos.
- Venta sigue recibiendo sólo cliente/renglones, rechaza vacío/repetidos/precio/total, copia precios y calcula total/subtotal Decimal. No existe PATCH de venta. Stock disponible, descuento y movimientos de ventas siguen pendientes del bloque de stock/UoW.
- Conflictos de integridad: 409 con texto propio; datos fuera de límites de DB: 422 con rollback y sin SQL ni trazas. Se conserva la separación 404 recurso de ruta / 409 referencia conflictiva.

### TDD Cycle Evidence

Safety net inicial: **44/44**. Antes de ejecutarla se instalaron las dependencias ya declaradas en `requirements-dev.txt` dentro de `.venv`; faltaban pytest y bcrypt. El primer arranque tuvo 41 aprobadas y tres errores de fixture por faltar `tmp/`, padre de `--basetemp=tmp/pytest`; se preparó ese directorio ignorado y la baseline completa quedó verde, sin cambiar pruebas ni producción para ocultarlo.

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| Entradas y PATCH | `test/test_contracts.py` | DTO | 44/44 | 26 fallos; después 6 de límites | 42/42 | campos extra, null, límites, cero/positivo, ventas inválidas | suite verde |
| Paginación compartida | `test/test_paginacion.py` | Unidad/SQL | 44/44 | módulo inexistente | 8/8 | vacío, final, rangos y filtros | suite verde |
| Listados y parámetros | `test/test_crud_http.py` | HTTP/routers, sesión controlada | 44/44 | 43 fallos; después 10 IDs | 54/54 | ocho listados x parámetros y null/IDs | suite verde |
| Alta y baja | `test/test_libros_crud.py` | HTTP/servicio | 44/44 | 6 fallos | 6/6 | stock cero/positivo y 204/404, 401 | suite verde |
| Errores propios | `test/test_errors.py` | Unidad | 44/44 | 2 DataError sin traducir | 4/4 | dos errores x dos mensajes internos | suite verde |
| Persistencia y relaciones | `postgres_tests/test_crud.py` | ASGI + PostgreSQL real | suite previa 29 conservada | 2 bajas en catálogo; 2 ventas de borrado | 8/8 nuevos | cero/positivo, búsqueda literal/case, FK rollback, ventas cantidades 1/3 | 37/37 total verde |

Los primeros intentos de nuevos tests necesitaron importar todos los modelos relacionados y corregir una suposición sobre el orden de parámetros SQL compilados; fueron arreglos de fixture, no cambios para evitar el comportamiento exigido. La ampliación PostgreSQL expuso que una venta aún admitía un libro borrado (201): se agregó el filtro de vigencia y el mismo caso pasó con 409.

Verificación final:

- `python -m pytest -q`: **158 passed in 8.60s**. Incluye las 44 pruebas anteriores; aviso de deprecación Starlette/httpx sin fallos.
- `PYTHONIOENCODING=utf-8 python scripts/test_postgres.py`: **37 passed in 6.36s**, cluster nuevo `tmp/postgres-tests-ff5a5264dd80`, puerto 54039. El runner ejecutó upgrade head -> downgrade base -> upgrade head y `alembic check` antes/después sin drift. Confirmó `server stopped` al salir.
- Se usa UTF-8 en el proceso de verificación porque una salida de fallo con caracteres españoles provocó UnicodeEncodeError en la consola cp1252; no se modificó el runner ni el entorno global. Los clusters de todos los intentos se detuvieron en finally.
- `git diff --check`: sin errores. Logs locales ignorados en la carpeta de cluster final (`verification.log`, `server.log`). No se ejecutó seed ni se alteró una base real.

### Próximo bloque actualizado

Ejercicio 4: registro/login/cookie y limitación de intentos, con DTO de registro sin roles/salidas sin hash; conectar `requerir_usuario_id` a validación real de sesión y permisos (coordinado con ejercicio 5). Después completar repositorios/UoW, stock/ventas atómicas y evidencias según el plan. La CLI OpenSpec ahora responde, pero `openspec list --json` informa `root:null`, `changes:[]`, `no_openspec_root`; las skills OpenSpec no se encontraron en ubicaciones activas. No se inicializó estructura OPSX ni se inventó un change para este bloque.

## Ejercicio 4 - autenticación (5 de noviembre de 2026)

Implementado en `master`, sin commit/push ni archive en este bloque. OpenSpec está inicializado desde el cierre del ejercicio 3; change activo `ejercicio-4-autenticacion`, con propuesta, especificación, diseño y tareas. Gobernanza CRITICAL con aprobación previa registrada en el plan. `Decision: no (no UI)`.

- Registro estricto sin roles: usuario, CLIENTE y cliente en una transacción; conflictos de correo de usuario o cliente dan 409 sin apropiación. Salidas explícitas sin hash.
- Login con bcrypt en hilo bajo semáforo; hash ficticio ante correo inexistente y mismo 401 ante clave incorrecta. Cinco fallos correo/IP en ventana de 60s bloquean el siguiente intento con 429/Retry-After sin bcrypt. Éxito reinicia conteo conservando historial. IP de conexión, sin confiar cabeceras de proxy.
- Cookie `access_token` HttpOnly/SameSite=Lax/Max-Age; JWT HS256 fijo, sub/exp requeridos. Roles token informativos; roles vigentes consultados en DB. No autentica Authorization. `/auth/yo`, logout público y cambio de contraseña documentados en README.
- Cambio de contraseña captura ID/hash y finaliza la lectura autobegin de la dependencia antes de verificar/generar hash; recarga dentro del UoW, verifica activo/hash sin cambios y guarda hash/flag/evento atómicamente. Conserva la misma cookie.
- Alta de libros conectada a actor real con ADMIN vigente y sin cambio obligatorio. Una revocación/vencimiento en DB afecta la misma cookie aunque el token conserve ADMIN.
- Repositorio/UoW del módulo usuarios: repositorio sólo flush; servicio abre UoW, éste confirma/revierte sin cerrar sesión compartida de petición. La migración del resto de módulos y las clases genéricas del ejercicio 6 siguen pendientes.
- Intentos de acceso usan sesión/transacción propias para sobrevivir rollback de login. Comentario obligatorio explica excepción y costo de conservar historial. Las pruebas inyectan errores tras flush para verificar rollback de registro y contraseña/evento.

Decisiones locales: mínimo de nuevas contraseñas 8 caracteres, máximo de todas 72 bytes UTF-8; HS256 y TTL default 1800 (`JWT_TTL_SECONDS`); `COOKIE_SECURE=false` para HTTP local, configurable true para HTTPS. La consigna no impone esos defaults. EmailStr normaliza dominio; parte local sensible a mayúsculas según UNIQUE actual. `.env` real y `despliegue/` intactos; no se cambiaron modelos ni migraciones, no seed ni bases ajenas.

### TDD Cycle Evidence

Baseline real previa a producción: **158/158** en 9.03s. PyJWT no estaba instalado; se agregó dependencia `PyJWT>=2.10,<3` y se instaló 2.15.1 sólo en `.venv`, antes de confirmar RED de primitivas ausentes.

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 Contratos/bcrypt/JWT | `test/test_auth_primitives.py` | DTO/unidad/hilo | 158/158 | verify_password inexistente | 15/15 inicial | límites UTF-8, claves/TTL, vencimiento y campos extra | suite verde |
| 2.1 Registro/login | `postgres_tests/test_auth.py` | ASGI/PostgreSQL | baseline 158; suite PG previa 37 | router inexistente | escenarios de registro/login verdes | correo usuario/cliente, 5 fallos sin enumeración, ventana60s/IP/éxito, rollback tras flush | 55/55 total |
| 3.1 Sesión/actor/cambio | `postgres_tests/test_auth.py` | ASGI/PostgreSQL | suite inicial conservada | router inexistente | cookie/sesión/cambio/actor verdes | Secure false/true; Bearer/vencido/inactivo/inexistente; ADMIN revocado/vencido/cambio; evento rollback | 55/55 total |
| Hash antes transacción | `test/test_auth_transactions.py` | Unidad servicio | 173/173 sin DB | cambio mantenía autobegin: 1 fallo | 2/2 | registro y cambio password | recarga tras rollback, suite verde |
| Sujeto JWT malformado | `test/test_auth_primitives.py` | Unidad | 17 unitarios auth verdes | sub 5000 dígitos lanzaba ValueError | 19/19 primitivas | enorme, entero, negativo, fuera de rango | límite previo a int, suite verde |

Verificación final: `python -m pytest -q`: **179 passed in 8.80s** (incluye 158 previas). Aviso de deprecación Starlette/httpx sin fallos. `PYTHONIOENCODING=utf-8 python scripts/test_postgres.py`: **55 passed in 13.39s**, de las cuales 18 nuevas de auth; cluster propio `tmp/postgres-tests-66353506987e`, puerto 63729, `server stopped` confirmado. Migraciones head -> base -> head, sin tablas/función remanentes tras base y `alembic check` sin drift antes/después. El único cambio posterior al runner fue endurecer longitud sub JWT (pruebas unitarias ejecutadas), docstring y documentación.

Los primeros intentos PG detectaron errores de fixture: importar modelos relacionados antes de inicializar mappers; commits reales de auth contaminaban las tablas que los tests anteriores esperaban vacías; ISBN de prueba uuid32 excedía max20. Se corrigieron los fixtures, sin relajar validaciones ni tests previos. Cleanup usa TRUNCATE sólo después de verificar directorio y base del cluster temporal propio; necesario por intentos independientes y movimientos sólo-agregado. Todos los clusters propios de los intentos quedaron detenidos.

### Próximo bloque

Ejercicio 5: gestión de personal/roles, permisos en toda la matriz, grupo protegido con control único de cambio obligatorio, propiedad de ventas y auditoría de cambios de rol. La comprobación ADMIN del alta es integración puntual, no finaliza ese ejercicio. Después, repositorios/UoW generales, stock/ventas atómicas, seed/evidencias y Docker/VPS según el plan.

### Formalización OPSX posterior (5 de noviembre de 2026)

Por pedido explícito del usuario se inicializó OpenSpec con Codex y se completó propose → apply → archive para `ejercicio-3-contratos-crud-paginacion`. La propuesta registra que el código ya existía; apply reconcilió seis tareas, sin modificar producción ni recrear TDD retrospectivo. Se repitió la suite sin DB: **158 passed in 9.20s**; las **37 pruebas PostgreSQL** se respaldan con el log íntegro anterior, sin presentarlas como nueva ejecución.

Archivo local: `openspec/changes/archive/2026-11-05-ejercicio-3-contratos-crud-paginacion/`. La CLI sincronizó ocho requisitos en `openspec/specs/contratos-crud/spec.md` y `openspec/specs/listados-paginados/spec.md`; `openspec validate --specs --strict`: **2 passed, 0 failed**. La lista de cambios activos quedó vacía. Se conservan explícitamente pendientes registro/auth4, permisos5, repositorios/UoW y stock de ventas; el alta sigue cerrada401 hasta integrar acceso. `openspec/` continúa ignorado por Git según la política existente; sin commit.

### Archivo OPSX del ejercicio 4 (5 de noviembre de 2026)

Por pedido explícito del usuario, se archivó `ejercicio-4-autenticacion` con las cuatro tareas completas y validación estricta aprobada. La CLI sincronizó seis requisitos en la nueva especificación `openspec/specs/autenticacion/spec.md` y creó `openspec/changes/archive/2026-11-05-ejercicio-4-autenticacion/`. Se verificó que el contenido sincronizado conserva propósito, requisitos y escenarios del delta. `openspec validate --specs --strict`: **3 passed, 0 failed**; `openspec list --json`: sin cambios activos. Se reutiliza la verificación inmediata de **179 pruebas sin DB y 55 PostgreSQL**, sin presentarla como otra ejecución. El ejercicio 5 y los demás pendientes indicados arriba siguen abiertos; el alta de libros ya utiliza autenticación y ADMIN vigente implementados en el ejercicio 4. Los artefactos OpenSpec siguen locales e ignorados por la política existente de Git.

## Ejercicio 5 — roles, permisos y propiedad (5 de noviembre de 2026)

Implementado en `master`, sin archive, commit ni push. OpenSpec: `ejercicio-5-roles-permisos`, propuesta/spec/diseño y cuatro tareas. Gobernanza CRITICAL previamente aprobada en el plan; sin UI (`Decision: no (no UI)`). No se modificaron `.env` real, `despliegue/`, modelos o migraciones.

- Alta de personal ADMIN/VENDEDOR con contraseña provisoria y cambio obligatorio, asignación con otorgante y evento en la misma transacción. Bcrypt se calcula antes de abrir escritura; se finaliza lectura de autenticación y se revalida ADMIN antes de persistir.
- Historial de roles completo; rol vigente repetido 409; reasignación vencida cierra fila anterior antes de crear otra. Vencimiento sin zona/pasado 422; autorrevocación ADMIN y ausencia de otro ADMIN vigente 409. Los controles son secuenciales, conforme a la exclusión de concurrencia del capítulo 7.
- Dos grupos de rutas en `main.py`, público y protegido. El control de cambio obligatorio está montado una única vez en el protegido. `requiere_rol` consulta DB en cada petición; no utiliza los roles informativos del token. Usuario actual, dependencias y UoW comparten sesión de petición.
- Escrituras de catálogo y administración sólo ADMIN; clientes/perfiles y registro/listado de ventas ADMIN o VENDEDOR. Los detalles adicionales existentes de autor/editorial permanecen públicos porque sólo exponen catálogo. No se agregaron todavía reposición ni consulta de movimientos del bloque de stock.
- `/mis-ventas` requiere sólo autenticación y filtra por `Cliente.usuario_id`; detalle de venta para personal vigente o dueño, incluso si ya no conserva rol CLIENTE. Tercero 403, inexistente 404. El cambio obligatorio bloquea ambos; `/auth` y catálogo siguen accesibles.
- `/eventos` paginado sólo ADMIN. Alta personal, asignación y revocación de roles registran evento dentro del mismo UoW; cambio de contraseña conserva la atomicidad del ejercicio 4. Seed agrega `SISTEMA` / `Carga de los datos iniciales` antes del commit. La carga ampliada de usuarios/roles/movimientos del ejercicio 8 permanece pendiente.

### TDD Cycle Evidence

Baseline ejecutada antes de producción: **179 passed in 9.27s**. Primera suite PG del bloque: 63/63 conservó las 55 previas, con 8 nuevos casos administrativos. El runner siempre utilizó un clúster nuevo propio; las comprobaciones de migraciones siguieron sin drift.

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| DTO personal/roles | `test/test_roles_contracts.py` | DTO | 179/179 | import PersonalCreate inexistente | 9/9 | dos roles personal, fechas sin zona/pasadas/futuras, extras | Verde |
| Administración e historial | `postgres_tests/test_roles.py` | ASGI/PostgreSQL | 55 previas conservadas | admin_router inexistente | 8 casos nuevos, 63 total | ADMIN/VENDEDOR, vencido/revocado, duplicado y rollback evento | Verde |
| Matriz y grupos | `test/test_permission_routes.py` | HTTP | 179/179 inicial | 21 rutas fallaron; después sólo mis-ventas404 | 21/21 | escrituras, privados, administración sin cookie | Verde |
| Propiedad/cambio obligatorio | `postgres_tests/test_roles.py` | ASGI/PostgreSQL | 63 PG | mis-ventas404; 4 casos fallaron | 67/67 total | dueño sin rol, personal, tercero, revocación misma cookie, cambio flag | Verde |
| Invariante ADMIN | `test/test_admin_invariants.py` | Servicio | Suites verdes | triangulación del bloque administrativo | 2/2 | cero/uno administradores restantes; sin escrituras en rechazo | Verde |
| Seed auditado | `test/test_seed_audit.py` | Unidad | 209/209 | 2 fallos: ningún evento | 2/2 | commit exitoso/fallido | Verde |
| Eventos y seed real | `postgres_tests/test_roles.py` | ASGI/PostgreSQL | 67/67 | extensión de escenarios del bloque | 4 adicionales, 71 total | ADMIN/VENDEDOR, última página/422, seed éxito/rollback | Verde |

Las fixtures CRUD anteriores ahora conceden explícitamente personal para probar contratos existentes; las pruebas nuevas de seguridad usan cookies y usuarios DB reales, sin esos overrides. El primer RED de matriz necesitó corregir una fixture que carecía de sesión (se sustituyó la sesión, sin añadir autenticación ficticia). La ampliación de limpieza del fixture auth incluye autores/géneros que el seed de pruebas carga; valida directorio/base del clúster antes del TRUNCATE. No se ejecutó seed sobre ninguna base ajena.

Verificación final: **213 passed in 8.79s** sin DB; **71 passed in 20.96s** PostgreSQL. Clúster final `tmp/postgres-tests-654473165456`, puerto **55725**, detenido por el runner. `upgrade head → downgrade base → upgrade head` y `alembic check` sin diferencias; logs ignorados `verification.log`/`server.log` en esa carpeta. Los clústeres de intentos previos también fueron detenidos por `finally`. `git diff --check` sin errores. Revisión independiente de permisos sin bloqueantes; se eliminó el control redundante de cambio obligatorio en el adaptador del actor de libro.

Sigue el ejercicio 6: base de repositorios/UoW y conversión de los CRUD anteriores, punto único de stock, reposición y ventas atómicas. Después, integridad/evidencias y seed ampliado/casos HTTP según los ejercicios 7 y 8. Los artefactos OpenSpec siguen locales e ignorados por Git.

### Archivo OpenSpec del ejercicio 5

Por pedido explícito del usuario, se archivó `ejercicio-5-roles-permisos` con cuatro tareas completas y validación estricta aprobada. La CLI sincronizó seis requisitos en `openspec/specs/autorizacion/spec.md` y creó `openspec/changes/archive/2026-11-05-ejercicio-5-roles-permisos/`. Se comprobó que propósito, requisitos y escenarios conservan exactamente el contenido del delta, normalizando sólo los saltos de línea y los encabezados propios de una especificación principal. `openspec validate --specs --strict`: **4 passed, 0 failed**; `openspec list --json`: sin cambios activos. La evidencia vigente sigue siendo **213 pruebas sin DB y 71 PostgreSQL**, sin nueva ejecución ni cambios de producción. OpenSpec continúa local e ignorado por Git; el commit y push del código se realizan separadamente en `master`.

## Ejercicio 6 — repositorios, UoW e inventario

Implementación completada en `master`: repositorios/UoW comunes y por módulo; servicios sin SQL ni sesión directa; stock compartido por alta, reposición y venta; movimientos con actor real y venta opcional; reposición e historial paginado sólo ADMIN. Ventas y descuentos revierten juntos ante fallos; baja e ISBN conservan historial. Contratos y endpoints en [PERSISTENCIA.md](PERSISTENCIA.md).

La recuperación comenzó con código parcial y 1/5 tareas: 234 pruebas sin DB verdes, pero la primera suite PostgreSQL tuvo 75 verdes y 2 fallos de fixture por actor ORM expirado tras rollback. Se corrigieron los overrides para recargar el actor sobre la misma sesión de petición. Se detectó además que `UsuarioRepository.add` devolvía None; RED ejecutado (1 fallo/7 verdes), corrección mínima heredando el método base, GREEN 8/8 y triangulación con dos usuarios. No se inventa evidencia RED de la implementación anterior. Las pruebas ampliadas cubren venta multilibro, historial tras vaciar identity map, rollback después de flush de movimiento, ISBN y permisos reales CLIENTE/VENDEDOR.

Validación final: **236 passed in 15.96s** sin DB y **83 passed in 41.29s** PostgreSQL. Cluster propio `tmp/postgres-tests-9354a085a777`, puerto **54553**, detenido y sin `postmaster.pid`. Upgrade/check/downgrade base/upgrade/check sin diferencias ni restos en base. OpenSpec `all_done`, **5/5 tareas**, validación estricta del change aprobada; specs principales **4/4** válidas. `git diff --check` limpio. Evidencia detallada local en `openspec/changes/ejercicio-6-repositorios-uow-stock/verification.md`.

Al cierre de esta implementación, sin archivo, commit ni push. La integridad del ejercicio 7, la precarga/asincronía del ejercicio 8 y el seed ampliado/materiales de entrega seguían pendientes. Concurrencia y Redis de los capítulos 7/8 están excluidos de la consigna. No se tocaron `.env`, `despliegue/`, modelos ni migraciones.

### Archivo y publicación del ejercicio 6

Posteriormente, por pedido explícito del usuario, el ejercicio 6 se archivó en `openspec/changes/archive/2026-11-05-ejercicio-6-repositorios-uow-stock/`, con seis requisitos sincronizados y seis specs principales válidas. El código se publicó en `origin/master` mediante commit `f689730`. Los artefactos OpenSpec siguen locales e ignorados por Git.

## Ejercicio 7 — integridad

Implementación y evidencia en `master`, sin archivar ni publicar este bloque. Change `ejercicio-7-integridad-evidencia`, sin UI (`Decision: no (no UI)`). Se conservaron el trigger de la cuarta migración y `HistorialAcceso`, cuyo comportamiento existente pasó las nuevas regresiones; no fue necesario cambiar producción, esquema o dependencias.

- C-14: `test/solo_agregado.sql` recibe `movimiento_id` explícito; exige ambos rechazos SQLSTATE 23514 y fila completa intacta, con savepoints y rollback final. La prueba ejecuta psql real de la instalación del servidor temporal para movimientos positivos/negativos y detecta el trigger deshabilitado con salida distinta de cero. El trigger se restaura en `finally`; sólo se toca el cluster propio validado.
- UPDATE que modifica el motivo, UPDATE sin cambios y DELETE se comprueban también con asyncpg para cantidades +3 y -1; los INSERT válidos siguen permitidos.
- Login incorrecto devuelve 401 y login correcto con error posterior en roles aborta la petición; ambos conservan su intento en otra sesión. La prueba compara sesiones y transacciones distintas, verifica desde una tercera sesión y exige que el evento testigo insertado en la petición haya revertido.
- Evidencia real, comandos reproducibles y límites en [ej7_integridad.md](../evidencia/ej7_integridad.md) y [c14_psql.txt](../evidencia/c14_psql.txt). El ejercicio 7 es integridad, no concurrencia; el 8 es precarga/asincronía, además de los materiales de seed/entrega aún pendientes.

Baseline previa a editar: **236 passed in 6.62s** sin DB; **83 passed in 22.83s** PostgreSQL, cluster `postgres-tests-4ac36b0dc713:63654` detenido. RED del nuevo SQL: cuatro fallos por archivo inexistente; primera implementación dos verdes/dos fallos por `psql 17` ignorando el argumento de `\quit 3`. Corrección mínima con excepción SQL y `ON_ERROR_STOP`: seis pruebas nuevas verdes (4 psql y 2 aislamiento), después **12 passed in 3.64s** con triangulación y UPDATE con/sin cambios. Las regresiones del trigger/historial existentes comenzaron verdes; no se atribuye un RED retrospectivo.

Validación final: **236 passed in 11.91s** sin DB y **91 passed in 25.75s** PostgreSQL. Cluster final `tmp/postgres-tests-07f6fd0b12e6`, puerto **52166**, detenido por el runner y sin `postmaster.pid`. Las cuatro migraciones completaron upgrade head → downgrade base → upgrade head; `alembic check` no detectó diferencias antes/después y downgrade base no dejó tablas de dominio ni función de trigger. Change válido en modo estricto y seis specs principales válidas. `git diff --check` limpio; revisión independiente del SQL sin hallazgos. No hubo cambios de producción, migraciones, dependencias, `.env`, `despliegue/`, seed ni base real. Evidencia TDD detallada en `openspec/changes/archive/2026-11-05-ejercicio-7-integridad-evidencia/verification.md`. El ejercicio 8 y el seed ampliado/materiales posteriores siguen pendientes.

### Archivo del ejercicio 7

Por pedido expl?cito del usuario, la CLI archiv? el change con 3/3 tareas en `openspec/changes/archive/2026-11-05-ejercicio-7-integridad-evidencia/`. Sincroniz? un requisito agregado en inventario y uno modificado en autenticaci?n, conservando los escenarios anteriores. Se verific? el contenido delta/main y las seis specs principales pasaron validaci?n estricta; no quedan cambios activos. Se reutiliza la evidencia inmediata de 236 pruebas sin DB y 91 PostgreSQL, sin presentarla como una nueva ejecuci?n. Los artefactos OpenSpec contin?an locales e ignorados por Git; c?digo, pruebas y evidencia se publican por separado en `origin/master`.

## Ejercicio 8 — lecturas sin N+1 y asincronía

Completado en `master`, change `ejercicio-8-lecturas-asincronia`, sin UI
(`Decision: no (no UI)`). No se modificaron producción, migraciones,
dependencias, `.env`, `despliegue/` ni una base real: la precarga, la tarea de
comprobante y el logger existentes pasaron las nuevas regresiones.

- C-15 mide ventas de dos y cuatro renglones con libros distintos y uno dado
  de baja: **2 SELECT** en repositorio y **4 SELECT** en HTTP con cookie real
  (usuario, roles y dos de detalle), iguales para ambos tamaños. Cada lectura
  empieza sin identidades precargadas y serializa después de cerrar sesión,
  con **0 SELECT** adicionales. Se cubren también listados por cliente/usuario,
  editorial/género, autorías/autor y cliente con/sin perfil. Contrato en
  [PERSISTENCIA.md](PERSISTENCIA.md), consultas reales y reproducción en
  [ej8_lecturas.md](../evidencia/ej8_lecturas.md).
- El orden ASGI observado es `commit → schedule → body → receipt`, una vez;
  409 y fallos de escritura/commit no agendan ni emiten aviso y no guardan venta.
  Dos unitarias comprueban espera cooperativa de 0.5 y log único posterior.
  Auditoría: 40/40 handlers propios asincrónicos, sin E/S bloqueante detectada.
- Dos ventas reales con uvicorn normal conservan su log de respuesta 201 seguido
  del comprobante con ID, destinatario y total. Procesos terminados en finally.
  [Log e instrucciones](../evidencia/ej8_comprobante.md) y
  [orden/auditoría](../evidencia/ej8_asincronia.md). `BackgroundTasks` puede
  perder avisos si termina el proceso; no es una cola durable.

Baseline antes de editar: **236 passed in 7.48s** sin DB y **91 passed in
27.12s** PostgreSQL. Las pruebas nuevas comenzaron verdes sobre comportamiento
existente: no se inventa evidencia RED retrospectiva. Focalizadas: C-15 3/3
(3.51s y ampliación 3.31s), orden ASGI 5/5 en 3.05s, espera/log 2/2 en 1.46s y
uvicorn 2/2 en 12.33s. Triangulación: dos/cuatro renglones, relaciones opcionales,
dos cantidades/totales y rechazo/fallos de escritura/commit.

Validación final: **238 passed in 9.62s** sin DB y **101 passed in 37.08s**
PostgreSQL. Cluster final `tmp/postgres-tests-5c714c16c1da`, puerto **50819**,
detenido y sin PID; todos los clusters propios de esta acción quedaron
detenidos. Migraciones head → base → head y check sin drift; base sin tablas
de dominio ni función de trigger. Change válido en modo estricto y seis specs
principales válidas; `git diff --check` limpio. Evidencia TDD en
`openspec/changes/ejercicio-8-lecturas-asincronia/verification.md`.

Sin archivar, commit ni push en esta acción. Seed ampliado, batería HTTP global,
empaquetado y Docker/VPS siguen pendientes; no se presentan como completados.

### Archivo del ejercicio 8

Por pedido del usuario, la CLI completo el archivo con 3/3 tareas en
`openspec/changes/archive/2026-11-05-ejercicio-8-lecturas-asincronia/`.
Sincronizo dos requisitos nuevos de comprobantes y uno modificado de
persistencia transaccional, conservando los escenarios existentes. Los
bloques delta/main coinciden y las siete specs principales pasan validacion
estricta; no quedan cambios activos. Se conserva la evidencia inmediata de
238 pruebas sin DB y 101 PostgreSQL, sin afirmar otra ejecucion. OpenSpec
continua local e ignorado; pruebas, evidencia y documentacion se publican
por separado en `origin/master`.

## Ejercicio 9 — contenedor del TP original

Implementación local sobre `despliegue/`, sin incorporar las ampliaciones del
parcial. Docker estaba instalado por usuario y activo, pero fuera de PATH:
`%LOCALAPPDATA%/Programs/DockerDesktop/resources/bin/docker.exe`.
Cliente y servidor **29.9.2**, motor Linux x86_64. No se instaló software ni
se activaron servicios. La detección inicial de ausencia de Docker era incompleta.

- Dockerfile `python:3.12-alpine`, instalación de wheels antes del código,
  sin compiladores ni caché de pip; usuario `app` UID **100**.
- Contexto exclusivo `despliegue/`, copias explícitas y `.dockerignore`;
  BuildKit confirmó exclusión de señuelos `.env`, `.venv`, `.git` y
  `__pycache__`. Sin URL/credenciales incorporadas a configuración o historial.
- Entry POSIX LF: URL requerida, `alembic upgrade head` y después `exec uvicorn`.
  `.gitattributes` conserva LF tras checkout en Windows. URL ausente y base
  inaccesible fallan sin iniciar HTTP. No se ejecuta seed en el arranque.
- HEALTHCHECK Python con `127.0.0.1:8000/health/ready` y timeout 2 s. Se observó
  healthy con base disponible, HTTP 503 y unhealthy al detener PostgreSQL,
  y recuperación a healthy al reiniciar exclusivamente el cluster propio.
- Primera app contra base vacía aplica las dos migraciones originales. La
  recreación conserva una editorial testigo y no vuelve a ejecutar revisiones.
  Ciclo head/check/base vacío/head/check sin drift. No se modificó el dominio,
  requirements, seed ni migraciones del TP; procedencia comparada contra
  `54c7fa2e362904999e07857636bb97f087877341`, normalizando sólo CRLF/LF.

Baseline antes de editar: **238 passed in 7.95s**. RED de Dockerfile: dos
archivos ausentes; GREEN 2/2. Entry/salud: RED 10 por archivos ausentes,
GREEN 10/10. Protección LF: RED 2 por atributo ausente, GREEN 2/2.
Triangulación: dos URLs, dos fallos de migración, URL ausente/vacía,
HTTP 200/503, timeout/conexión, señuelos reales y estado sano/caído/recuperado.
Focalizadas finales: **16 passed in 5.18s**. Suite completa sin DB:
**254 passed in 12.70s**. La suite PostgreSQL del parcial de 101 casos corresponde
al ejercicio 8; no se repitió porque no cambió su producción ni esquema.
El esquema del TP sí se comprobó en una base externa temporal nueva.

La base de imagen inspeccionada ocupa **74 102 118 bytes** y la final
**249 753 877 bytes**: el límite de 100 MB se aplica a la base. Ver comandos,
versiones, salidas reales y limpieza en
[docker_local.txt](../despliegue/evidencia/docker_local.txt), instrucciones en
[DEPLOY.md](../despliegue/DEPLOY.md) y evidencia TDD detallada local en
`openspec/changes/ejercicio-9-docker-tp/verification.md`.

El verificador final terminó con código **0**: cluster propio
`tmp/docker-tests-1fdfdcec7b17`, PostgreSQL **60523**, app **60524**.
Los contenedores y la imagen propios fueron eliminados; los tres clusters de
los intentos quedaron detenidos y sin `postmaster.pid`. La base Python
descargada y los recursos ajenos se conservaron. Validación estricta del
change aprobada, siete specs vigentes válidas y `git diff --check` limpio.

## Ejercicio 10 — simulación local de despliegue (6 de noviembre de 2026)

Por decisión del usuario, D-02/D-03/D-04/D-08 se simularon localmente con Docker Desktop 29.9.2 y un PostgreSQL temporal externo al contenedor. El runner crea datos efímeros nuevos, escribe un env temporal fuera del contexto, publica HTTP sólo en `127.0.0.1` y elimina únicamente los recursos que creó. El seed se ejecutó exclusivamente sobre esa base temporal vacía.

- D-02 local: primer inicio aplicó las dos migraciones; `/health/ready` dio 200. Caída de PostgreSQL: 503 y estado `unhealthy`; recuperación: `healthy`.
- D-03 local: catálogo 200 y venta 201, cliente Tomás, dos Rayuelas, total `50000.00`.
- D-04 local: la venta siguió accesible tras eliminar y recrear el contenedor; no se repitieron migraciones.
- D-08 local: el log de comprobante de venta #3 apareció después de la respuesta 201.
- `python -m pytest -q`: **257 passed**. Runner Docker punto 10 completado con exit 0 y runner del punto 9 repetido con exit 0. Migraciones head/check/base/head/check sin drift.
- Limpieza confirmada: contenedores e imagen propios eliminados y PostgreSQL temporal detenido.

La guía resumida y la salida real están en `despliegue/evidencia/ejercicio10_simulacion_local.md` y `despliegue/evidencia/vps_local_simulation.txt`. Esto no acredita acceso público ni permanencia de un VPS. Siguen pendientes los casos reales D-02/D-03/D-04/D-08 en VPS, el seed ampliado, materiales globales y empaquetado final.
