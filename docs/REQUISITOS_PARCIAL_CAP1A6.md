# Requisitos verificables del parcial Cap1a6

Fuente: `docs/Parcial_Cap1a6_Consigna.pdf`, 24 páginas, leído íntegramente el 5 de noviembre de 2026. Esta matriz sirve para implementar y verificar; no afirma que los requisitos ya estén cumplidos. Las páginas indicadas son las impresas en el PDF.

El PDF contiene **10 ejercicios**: 1 a 8 corresponden al proyecto ampliado; 9 y 10 corresponden al TP original empaquetado y desplegado. El resumen inicial de planificación no sustituye este detalle ni la fuente.

## Alcance y estructura

- Partir del TP propio entregado, capítulos 1 a 4.
- Entrega grupal única: `Parcial_Cap1a6_<NombreDelGrupo>.zip` con `parcial/` y `despliegue/` como proyectos distintos.
- `parcial/` contiene usuarios, acceso, roles, transacciones, stock, repositorios y UoW.
- `despliegue/` contiene el TP 1 a 4 preservado, Docker y evidencia VPS. No recibe las ampliaciones funcionales del parcial. Si un defecto del TP impide cumplir su funcionamiento en el contenedor, se corrige y se documenta en `DEPLOY.md`.
- No se evalúan concurrencia/bloqueos del capítulo 7 ni Redis/colas del capítulo 8. El aviso de venta es simulado con `BackgroundTasks` y puede perderse si se reinicia el proceso.
- Módulos mínimos: `health`, `usuarios`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`. `health` sólo necesita router.
- Por módulo funcional: `models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`.
- Compartidos obligatorios: `app/core/config.py`, `database.py`, `security.py`, `dependencies.py`, `repository.py`, `paginacion.py`, `unit_of_work.py`.
- `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` viven en `usuarios`; `MovimientoStock` y `LibroAutor` en `libros`; `PerfilCliente` en `clientes`; `RenglonVenta` en `ventas`.

## Configuración y ciclo de vida - ejercicio 1 (6 puntos)

Incluido para que el bloque de base no dependa de parámetros inferidos; detalle en páginas 4 y 9.

| Requisito | Aceptación |
|---|---|
| Settings | pydantic-settings >=2.0, entorno o `.env` no versionado. |
| URL | `@computed_field` construye dirección con `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`; driver `postgresql+asyncpg`. |
| Secretos | Contraseña PostgreSQL y clave de firma sin valores por defecto; si faltan no arranca. No generar una clave nueva en cada arranque. `env.example` enumera todas las variables sin secretos. |
| Recursos | Motor asincrónico, pool cuyo tamaño está en Settings y fábrica de sesiones se construyen en lifespan, se guardan en `app.state`; nunca al importar módulos. |
| Sesión | `get_session` usa fábrica de `app.state`, una sesión por petición, `expire_on_commit=False`, la cierra al terminar. |
| Hash ficticio | Se calcula una vez en lifespan para login contra correo inexistente. |
| Apagado | Cierre del motor mediante `dispose()`. |
| Salud | `/health/live` no consulta DB; `/health/ready` ejecuta `SELECT 1`, 503 si DB no contesta. |

## Modelos, relaciones y migraciones - ejercicio 2 (10 puntos)

Páginas 4 a 6 y 10. Los nombres siguientes son obligatorios: se pueden agregar columnas, no quitar ni renombrar las indicadas.

| Tabla | Columnas obligatorias | Restricciones y relaciones |
|---|---|---|
| `usuario` | `id`, `email`, `nombre`, `password_hash`, `activo`, `debe_cambiar_password` | `email` UNIQUE. No tiene columna `rol`. |
| `asignacion_rol` | `id`, `usuario_id`, `rol`, `desde`, `vence_en` nullable, `revocada_en` nullable, `otorgada_por` nullable | CHECK rol en ADMIN/VENDEDOR/CLIENTE. Índice UNIQUE parcial `(usuario_id, rol) WHERE revocada_en IS NULL`. Historial no se borra. |
| `intento_acceso` | `id`, `cuando`, `email`, `ip`, `exito` | Índice compuesto `(email, ip, cuando)`. No se relaciona con otras tablas. |
| `evento_seguridad` | `id`, `cuando`, `actor` texto, `accion` | Sin restricciones adicionales. Actor no es FK a usuario; permite `SISTEMA`. No se relaciona con otras tablas. |
| `movimiento_stock` | `id`, `libro_id`, `venta_id` nullable, `usuario_id`, `cantidad`, `motivo`, `cuando` | Cantidad distinta de cero; sólo agregado protegido por trigger. |
| `cliente` existente | Agregar `usuario_id` nullable | FK a usuario y UNIQUE, además del UNIQUE de `email` existente. `Cliente.usuario` es objeto, no lista. |
| `libro` existente | Agregar `borrado_en` nullable | UNIQUE parcial `(isbn) WHERE borrado_en IS NULL` reemplaza UNIQUE común; conservar CHECK `precio > 0` y `stock >= 0`. |

Todas las fechas nuevas llevan zona (`timestamptz`). Cada FK nueva lleva índice; declarar navegación en ambos extremos. Mantener dinero `NUMERIC`/`Decimal`, nunca `float`. No cambian `editorial`, `genero`, `autor`, `libro_autor`, `perfil_cliente` respecto del TP.

**Migraciones obligatorias**:

1. Conservar las dos del TP.
2. Tercera: generada mediante `alembic revision --autogenerate`; incorpora nuevas tablas y cambios de cliente/libro, incluidos índices `postgresql_where`. Leer antes de aplicar; comentario indica revisión y cualquier corrección manual de la salida generada.
3. Cuarta: escrita a mano; función y trigger que rechazan UPDATE/DELETE en `movimiento_stock`. También comentario de revisión.
4. Verificar en base vacía `alembic upgrade head` -> `alembic downgrade base` -> `alembic upgrade head`.
5. Esquema exclusivamente Alembic; aplicación sin `create_all`.

La semántica de la cantidad del movimiento es **no cero**, para permitir altas/reposiciones positivas y ventas negativas. El texto extraído automáticamente distorsiona algunos símbolos; no interpretar la celda como cantidad positiva solamente.

## Contratos y CRUD - ejercicio 3 (8 puntos)

Página 10 y ejemplos en páginas 18 a 19.

- DTO separados de modelos de tabla; entradas con `extra="forbid"`. Ninguna salida expone `password_hash`.
- Registro no recibe roles. PATCH de libro no recibe `stock`; actualiza título/precio según referencia. Aplicar sólo campos enviados (`exclude_unset`).
- 201 al crear; 204 al dar de baja libro; 404 recurso de ruta inexistente; 409 conflicto con datos guardados; 422 cuerpo/parámetros inválidos. Errores propios, sin texto SQL/DB/trazas. Ninguna entrada inválida termina en 500.
- En todos los listados usar `{items, total, page, size, pages}`. `page >= 1`; `size` 1..100, default 20. `total` usa exactamente los filtros de la página. `pages` se calcula del total y tamaño; con total 0 hay una página vacía. Página posterior a la última: 422.
- Búsqueda por título sin distinguir mayúsculas y con parámetros ligados; no concatenar entrada a SQL.
- Venta: cuerpo sólo `cliente_id` y `renglones` con `libro_id`/`cantidad`; al menos un renglón, sin libros repetidos. Precio, fecha y total no se reciben; precios copiados del libro y total calculado por servidor con Decimal. No existe PATCH de venta.
- Alta de libro recibe `stock_inicial` en lugar de `stock`, y autores con `autor_id`, `rol`, `orden`. Registrar movimiento con motivo `Stock inicial`.

## Autenticación - ejercicio 4 (14 puntos)

Página 11, RN-02/07/08 y referencia de endpoints.

| Área | Criterio exacto |
|---|---|
| bcrypt | Costo en configuración; toda llamada fuera del bucle mediante `to_thread` y bajo semáforo de concurrencia. Calcular hash antes de abrir transacción. |
| Longitud | Todo campo que llega a bcrypt admite como máximo **72 bytes**, medidos en UTF-8: nueva contraseña, login y contraseña actual para cambio. No confundir caracteres con bytes. Exceso: 422 antes de llamar bcrypt. |
| Auto-registro | Crear usuario, asignación CLIENTE y ficha de cliente en una transacción: las tres filas o ninguna. Correo de usuario repetido o de cliente existente: 409; no apropiarse de ficha existente. |
| Orden login | Primero límite de intentos por correo/IP. Si bloqueado: 429 con `Retry-After` y **sin bcrypt**. Luego verificar contraseña contra hash real o ficticio si correo no existe. |
| Límite | Después de 5 fallos para mismo correo y misma IP en 60 s, el siguiente intento se bloquea. Un login correcto reinicia cuenta; los fallos anteriores permanecen en tabla, dejan de contar. |
| No enumeración | Correo inexistente y contraseña incorrecta dan mismo cuerpo 401 y tiempo parecido. |
| Token | PyJWT firmado con `sub`, `exp` y roles vigentes al emitir. Esos roles informan; no autorizan. |
| Cookie | Nombre **`access_token`**, `HttpOnly`, `SameSite=Lax`, `Max-Age` igual a duración del token; `Secure` configurable. Sólo se lee de `request.cookies`; Authorization Bearer no autentica. |
| Respuesta login | No contiene token. Ejemplo del PDF: `mensaje`, `debe_cambiar_password`, `expira_en_segundos`. El valor de ejemplo es 1800 s. |
| Logout | Borra cookie; puede usarlo cualquiera. |
| Sesiones y cambio | Cambiar contraseña no invalida sesiones existentes ni emite token nuevo; misma cookie sirve después. Sesión dura hasta vencimiento o logout. |
| `/auth/yo` | Devuelve usuario, roles vigentes en DB y roles informados por token. |

**Parámetros que el PDF no fija**: algoritmo JWT concreto, duración obligatoria del token (1800 es ejemplo), costo numérico bcrypt, cantidad de permisos del semáforo, mínimo de contraseña y nombres exactos de campos DTO del cambio. Elegir y documentar al implementar; no presentarlos como valores exigidos. La existencia de Settings y el costo configurable sí son obligatorios.

## Autorización - ejercicio 5 (12 puntos)

Página 11, RN-03/04/05/06/14/16, matriz de rutas en páginas 16 a 18.

- `get_usuario_actual`: 401 sin cookie, token inválido/vencido, usuario inexistente o inactivo.
- `requiere_rol`: consulta roles vigentes en DB **en cada petición**, 403 si faltan. Revocación debe afectar inmediatamente la misma sesión, aunque token diga que tiene el rol.
- Roles vigentes: asignaciones no revocadas y sin vencer; son filas de `asignacion_rol`, no columna de usuario. Conservar historial al revocar (`revocada_en`).
- A lo sumo una asignación abierta por usuario/rol mediante índice parcial. Reasignar rol vencido cierra fila anterior y abre una nueva. Rol ya abierto/vigente: 409.
- Vencimiento opcional; si se envía, tiene zona y está en futuro. Fecha sin zona o pasada: 422.
- ADMIN no puede revocarse su propio ADMIN; nunca dejar cero administradores vigentes: 409.
- Alta de personal usa contraseña provisoria y cambio obligatorio.
- En `main.py`, **dos grupos de rutas**. Control de cambio obligatorio montado una sola vez en grupo protegido. Mientras está pendiente, sólo `/auth` y rutas públicas funcionan; protegidas 403.
- Lo propio sólo exige autenticación. `/mis-ventas` devuelve sólo ventas propias. Detalle de venta permite personal o cliente dueño; ajeno 403. No montar `requiere_rol` de personal en ese detalle.
- Alta de personal, cambio de rol y cambio de contraseña dejan evento en la **misma transacción** del cambio. Seed registra evento actor `SISTEMA`, acción `Carga de los datos iniciales`.

### Matriz de endpoints

Las rutas se expresan como aparecen en la referencia; todos los parámetros de ruta deben validarse. Cada ruta protegida agrega 401 sin sesión y 403 si cambio obligatorio pendiente.

| Grupo | Método y ruta | Acceso | Códigos de referencia |
|---|---|---|---|
| Abierto | GET `/health/live` | Público | 200 |
| Abierto | GET `/health/ready` | Público | 200, 503 |
| Abierto | POST `/auth/registro` | Público | 201, 409, 422 |
| Abierto | POST `/auth/login` | Público | 200, 401, 422, 429 |
| Abierto | POST `/auth/logout` | Público | 200 |
| Abierto | GET `/auth/yo` | Autenticado | 200, 401 |
| Abierto | POST `/auth/cambiar-password` | Autenticado | 200, 401, 422 |
| Abierto | GET `/libros` (`page`, `size`, `titulo`, `genero_id`) | Público | 200, 422 |
| Abierto | GET `/libros/{id}` | Público | 200, 404, 422 |
| Abierto | GET `/editoriales`, `/generos` (`page`, `size`) | Público | 200, 422 |
| Abierto | GET `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` | Público | 200, 404 |
| Protegido | POST `/usuarios` | ADMIN | 201, 409, 422 |
| Protegido | GET `/usuarios/{id}/roles` | ADMIN | 200, 404 |
| Protegido | POST `/usuarios/{id}/roles` | ADMIN | 201, 404, 409, 422 |
| Protegido | DELETE `/usuarios/{id}/roles/{rol}` | ADMIN | 200, 404, 409 |
| Protegido | GET `/eventos` (`page`, `size`) | ADMIN | 200, 422 |
| Protegido | POST `/editoriales`, `/generos`, `/autores` | ADMIN | 201, 409, 422 |
| Protegido | PATCH `/editoriales/{id}`, `/autores/{id}` | ADMIN | 200, 404, 409, 422 |
| Protegido | POST `/libros` | ADMIN | 201, 409, 422 |
| Protegido | PATCH `/libros/{id}` | ADMIN | 200, 404, 409, 422 |
| Protegido | DELETE `/libros/{id}` | ADMIN | 204, 404 |
| Protegido | POST `/libros/{id}/reponer` | ADMIN | 200, 404, 409, 422 |
| Protegido | GET `/libros/{id}/movimientos` | ADMIN | 200, 404 |
| Protegido | POST `/clientes` | ADMIN o VENDEDOR | 201, 409, 422 |
| Protegido | GET/PATCH `/clientes/{id}` (con perfil) | ADMIN o VENDEDOR | 200, 404, 409, 422 |
| Protegido | POST `/clientes/{id}/perfil` | ADMIN o VENDEDOR | 201, 404, 409 |
| Protegido | GET `/clientes/{id}/ventas` | ADMIN o VENDEDOR | 200, 404 |
| Protegido | POST `/ventas` | ADMIN o VENDEDOR | 201, 409, 422 |
| Protegido | GET `/ventas` (`page`, `size`) | ADMIN o VENDEDOR | 200, 422 |
| Protegido | GET `/ventas/{id}` | Personal o cliente dueño | 200, 403, 404 |
| Protegido | GET `/mis-ventas` (`page`, `size`) | Autenticado | 200, 422 |

## Repositorios y Unit of Work - ejercicio 6 (16 puntos)

Página 12; capa por capa: Router -> Service -> UoW -> Repository -> Model.

| Pieza | Obligación |
|---|---|
| `BaseRepository[T]` | Constructor recibe sesión **y clase de modelo**. Al menos `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`. |
| `SoftDeleteRepository[T]` | Hereda de base, usado por Libro, filtra dados de baja; agrega `get_by_id_including_deleted` y `soft_delete`, que no existen en base. |
| Escrituras repo | `add` y `update` hacen flush, nunca commit. Ningún repositorio confirma. |
| Repositorios entidades | Cada entidad tiene repositorio, métodos nombrados por lo que traen. Precarga declarada dentro de método que la necesita. |
| UoW base | Gestor contexto async; confirma al salir normalmente, revierte si excepción; **no cierra sesión**. |
| UoW de módulo | Compone repositorios necesarios, misma sesión. |
| Router | Construye UoW mediante dependencia, lo pasa al servicio sin abrir. |
| Servicio | Recibe UoW, lo abre con `async with`; nunca lo construye ni recibe sesión en lugar de UoW. |
| Sesión autenticada | Dependencias de usuario actual/rol y UoW comparten sesión de petición; no dos conexiones por autenticación. |
| Atomicidad | Un solo bloque para registro usuario+rol+cliente, venta+renglones+stock+movimientos, y cada cambio con su evento. |
| Stock | Un único punto de escritura usado por alta, reposición y venta. Cada modificación deja movimiento; `libro.stock = SUM(movimiento_stock.cantidad)` para cada libro. |

Validar stock disponible; si alguno no alcanza, 409 y ninguna escritura parcial. Libro borrado no se vende ni repone: 409. Libro borrado desaparece del catálogo pero su información sigue en ventas históricas. Reutilizar ISBN sólo después de baja; segundo vigente mismo ISBN 409. La unicidad la garantiza DB; no sustituir UNIQUE por consulta previa.

## Integridad - ejercicio 7 (10 puntos)

Página 12.

- Cuarta migración instala trigger que rechaza **cualquier UPDATE/DELETE** en `movimiento_stock`, incluso SQL directo fuera de API.
- Cada intento de login correcto o fallido se registra en sesión y transacción **propias**, confirmadas independientemente de rollback de petición.
- Es la única escritura que no comparte transacción de petición. Comentario obligatorio explica: qué hace distinto; por qué el fallo que cuenta revierte la transacción normal; costo de dejar filas aun si petición falla.
- No se exige revocar permisos UPDATE/DELETE al rol PostgreSQL: usa un solo rol; el trigger basta. No agregar ese requisito como si fuera obligatorio.

## Lecturas sin N+1 y asincronía - ejercicio 8 (6 puntos)

Página 13.

- Toda relación incluida en salida llega mediante precarga en repositorio, nunca lazy loading.
- Detalle de venta incluye cliente, renglones y libro de cada renglón, incluso borrado. Cantidad de consultas fija, sin crecer con número de renglones.
- Todos handlers `async def`, sin llamadas bloqueantes.
- Tras confirmar venta, agendar comprobante con `BackgroundTasks`: `await asyncio.sleep(0.5)` y mensaje en log. Corre después de respuesta y sólo si operación confirmó.
- Mensaje visible con arranque normal de uvicorn; configurar logger propio si necesario.

## Datos iniciales exigidos

Páginas 19 a 20. `seed.py` forma parte de puesta en marcha, vacía y repuebla de forma conocida; contraseñas ficticias sólo allí. No ejecutar contra base con datos ajena a pruebas/desarrollo confirmado.

| Entidad | Datos mínimos |
|---|---|
| Usuarios | `admin@example.com` y `admin2@example.com` ADMIN; `vendedor@example.com` VENDEDOR; `ana@example.com` CLIENTE; `nuevo@example.com` VENDEDOR con cambio obligatorio. |
| Catálogo base | 3 editoriales, 3 géneros, 6 autores del TP. |
| Libros y stock final | Rayuela 10; Antología de la literatura fantástica 5; Ficciones 8; Respiración artificial 3; Bestiario 1. |
| Clientes | Lucía Fernández con perfil y Tomás Ríos, ambos sin usuario; Ana Paz vinculada a `ana@example.com`. |
| Venta 1 | Lucía, registrada por vendedor, 1 Rayuela + 2 Ficciones, total `69000.00`. |
| Movimientos | Un `Stock inicial` por libro: Rayuela 11, Ficciones 10; venta 1 deja -1 y -2. Resto inicial igual a stock final. Debe cuadrar suma para los cinco libros. |
| Auditoría | Evento actor `SISTEMA`, acción `Carga de los datos iniciales`. |

La tabla del modelo de venta no se amplía con una columna de vendedor obligatoria; el registro del vendedor se representa al menos en `movimiento_stock.usuario_id`. Se permite agregar columnas si se justifica, no inferirlas como requisito expreso.

## Casos mínimos del parcial C-01 a C-16

Páginas 21 a 22. Incluir `.http` en `test/`, comentario con respuesta esperada por caso; ejecutar `python seed.py` antes de cada archivo para restablecer estado. Además `test/solo_agregado.sql` C-14 y evidencia real C-14/C-15 en `evidencia/`.

| Caso | Escenario y resultado esperado |
|---|---|
| C-01 | Sesión iniciada, parámetro ruta no entero ->422 antes de handler. |
| C-02 | Registro ->201; correo repetido usuario o cliente ->409 propio, sin filas sueltas de registro rechazado. |
| C-03 | Set-Cookie HttpOnly/SameSite=Lax/Max-Age; cuerpo sin token; sin cookie o sólo Authorization Bearer ->401. |
| C-04 | Correo existente+clave incorrecta vs inexistente ->mismo cuerpo 401 y tiempo parecido. |
| C-05 | Seis fallos consecutivos ->sexto429 con Retry-After, pocos ms y sin bcrypt; cinco fallos persistidos. |
| C-06 | Sin sesión401; vendedor creando libro403; cliente ve venta propia200, ajena403. |
| C-07 | Revocar rol con cookie abierta ->siguiente pedido403 misma cookie; `/auth/yo` muestra DB/token distintos; fila revocada permanece. Vencimiento pasado/sin zona422. |
| C-08 | ADMIN intenta revocar su propio ADMIN ->409. |
| C-09 | Usuario con cambio pendiente403 salvo auth/públicas; cambio deja bandera falsa y misma cookie sirve200 sin relogin. |
| C-10 | Venta válida dos renglones ->201 precios y total; stock descontado y movimiento por renglón; aviso en log después de respuesta. |
| C-11 | Rayuela1 disponible + Bestiario2 cuando hay1 ->409; ni venta/descuento/movimientos; Rayuela sigue10; suma=stock en cinco libros. |
| C-12 | Venta cliente inexistente, libro inexistente o libro borrado ->409 en tres variantes, sin escrituras. |
| C-13 | Reposición200 con movimiento; baja204; no aparece catálogo; mismo ISBN alta201, segundo vigente409; venta vieja conserva título. |
| C-14 | UPDATE y DELETE directo psql sobre movimientos ->ambos rechazados por trigger. |
| C-15 | Detalle venta2 vs4 renglones ->misma cantidad consultas visibles. |
| C-16 | Inyección `' OR '1'='1` ->items vacíos/total0; `titulo=ficc&size=1` ->total1/pages1; page2 ->422; size500 ->422; PATCH cambia sólo enviado; stock por PATCH422. |

## Docker y VPS - ejercicios 9 y 10 (11 y 7 puntos)

Páginas 14 a 16. Se trabaja en TP 1 a 4 preservado, no parcial. **Sin Docker Compose** ni base dentro de contenedor: PostgreSQL ya está en servidor.

| Requisito | Aceptación |
|---|---|
| Base imagen | `python:3.12-alpine`; límite100MB corresponde a **base**, no imagen final con dependencias. PDF dice que dependencias se instalan sin compilador. |
| Capas | Copiar/instalar `requirements.txt` antes de copiar código; pip `--no-cache-dir`. |
| Usuario | Crear usuario sin privilegios y activar `USER`; proceso no root. |
| Secretos | `.dockerignore` excluye `.env`, `.venv`, `.git`, `__pycache__`; Dockerfile/capas sin URL ni contraseña. |
| Inicio | `alembic upgrade head` y luego uvicorn `app.main:app --host 0.0.0.0`; si migración no conecta, termina con error, no queda sirviendo. |
| Salud | HEALTHCHECK GET `/health/ready` usando **127.0.0.1**, no localhost: evitar resolución IPv6 del wget Alpine. |
| Docker run | Publicar sólo app `-p <puerto-asignado>:8000`; `--restart unless-stopped`; `--env-file` externo repo/imagen; nombre ejemplo libreria. |
| Entorno TP | `DATABASE_URL` driver asyncpg con datos cátedra; `SQL_ECHO=false` o equivalente del TP. Host no localhost dentro contenedor. |
| Host PostgreSQL | Si corre en host: `host.docker.internal`; Linux agrega `--add-host=host.docker.internal:host-gateway`, salvo otra dirección cátedra. |
| VPS | Construir allí o transportar imagen, elegir/documentar. Accesible externamente hasta publicación notas. Seed del TP dentro contenedor después de levantar, sólo con destino/autorización confirmados. |
| DEPLOY.md | URL pública, día/hora, comandos build/run completos con nombre de archivo variables sin contenido; correcciones TP necesarias; actualización reconstruye imagen, elimina/recrea contenedor; datos persisten en PostgreSQL servidor. |

### Casos D-01 a D-08

Guardar comandos y salidas reales de cada caso en `despliegue/evidencia/`.

| Caso | Resultado esperado |
|---|---|
| D-01 | `docker images`: base Alpine<100MB y Dockerfile la usa; mostrar imagen final también. |
| D-02 | Build/run en servidor limpio: contenedor healthy; logs muestran migraciones TP aplicadas al arrancar. |
| D-03 | Desde fuera VPS: ready200; libros200 con seed; venta ejemplo TP201 con precios/total calculados. |
| D-04 | Eliminar contenedor y correr mismo run: healthy y datos siguen, migraciones ya aplicadas no se vuelven a ejecutar. |
| D-05 | Imagen sin DATABASE_URL termina error; no queda sirviendo. |
| D-06 | Contenido imagen sin `.env`; ejecutar `ls -a /app` y `env` con entrypoint alternativo; ninguna DATABASE_URL ni contraseña horneada. |
| D-07 | `docker exec libreria id` demuestra proceso no root. |
| D-08 | Aviso comprobante de venta D-03 aparece en docker logs después de línea respuesta. |

## Entrega y decisiones pendientes reales

- `parcial/`: fuentes, requirements, env.example, alembic.ini, migrations, test, README con integrantes y puesta en marcha completa desde cero (incluye generar clave firma), evidencia C14/C15.
- `despliegue/`: TP original, Dockerfile, .dockerignore, env.example de contenedor sin valores reales, DEPLOY.md, evidencia de cada D.
- ZIP sin `.env`, `.venv` ni `__pycache__` en ambas carpetas. Si se incluye `.git`, también se revisa historial de secretos.
- Fecha de entrega: campus, no informada en PDF. Datos/puerto VPS: cátedra, no informados aquí. No inventar URL, credenciales, despliegue o evidencia.
- `main.py` en tabla de estructura debe coordinarse con el módulo de arranque existente; el PDF exige explícitamente `app.main:app` para contenedor. No hace falta duplicar entrypoints sin necesidad.
- La raíz actual puede seguir siendo el proyecto ampliado durante desarrollo y empaquetarse luego como `parcial/`; preservar TP con procedencia verificable para `despliegue/` evita mezclarlo. La organización de desarrollo es decisión del proyecto, no requisito extra del PDF.
- Algoritmo/TTL y validaciones no fijados deben quedar documentados al elegirlos; no bloquear por una cifra que el PDF no exige.
- Las evidencias deben generarse ejecutando los casos; este documento no constituye evidencia de que pasaron.
