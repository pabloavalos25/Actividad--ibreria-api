# Librería API — parcial capítulos 1 a 6

API asincrónica con FastAPI, SQLModel y PostgreSQL. Continúa el TP de capítulos 1 a 4 de Programación III (UTN).

Integrantes: Pablo Avalos, Ismael Suarez y Sofia Blangetti.

El parcial está en desarrollo. Los ejercicios 1 a 9 están implementados y verificados. El punto 10 se simuló localmente con Docker y PostgreSQL efímero; la evidencia local no demuestra disponibilidad pública de un VPS. Siguen pendientes los datos de acceso al servidor, seed ampliado y materiales globales de entrega. Ver [progreso y evidencia TDD](docs/PROGRESO_PARCIAL_CAP1A6.md) y [requisitos completos](docs/REQUISITOS_PARCIAL_CAP1A6.md).

## Acceso (ejercicio 4)

- `POST /auth/registro`: `{nombre,email,password}`, crea usuario+CLIENTE+cliente atómicamente (201). Correo ya registrado como usuario o cliente: 409. No acepta roles ni devuelve hash.
- `POST /auth/login`: `{email,password}`, devuelve mensaje/flag/expiración y establece cookie `access_token`; no entrega token en JSON. Cinco fallos de correo/IP en 60 segundos bloquean el siguiente intento con 429 y `Retry-After`. Un éxito reinicia el conteo sin borrar historial.
- `GET /auth/yo`: usuario sin hash, `roles_vigentes` de DB y `roles_token` informativos. Sólo cookie autentica; `Authorization` no se utiliza.
- `POST /auth/cambiar-password`: `{password_actual,password_nueva}`, actualiza hash/flag y evento en una transacción; la misma cookie sigue funcionando. `POST /auth/logout` borra cookie y es público.
- Nuevas contraseñas: mínimo 8 caracteres; todas admiten como máximo 72 bytes UTF-8. Son decisiones del proyecto, al igual que HS256 y TTL por defecto 1800s (`JWT_TTL_SECONDS`). `COOKIE_SECURE=false` permite desarrollo HTTP local; usar true bajo HTTPS. Cookie HttpOnly y SameSite=Lax. Mantener `JWT_SECRET` aleatorio y fuera de Git.
- Email usa la validación EmailStr (normaliza dominio); la parte local conserva mayúsculas y la comparación coincide con el UNIQUE PostgreSQL sensible a mayúsculas. No se unifican fichas existentes silenciosamente.
- Los intentos se confirman en una sesión independiente para sobrevivir al rollback del login. La IP viene de la conexión; no se confía en `X-Forwarded-For`.

Los endpoints anteriores usan repositorio y UoW del módulo usuarios, compartiendo sesión de petición con autenticación. Los CRUD anteriores aún deben migrarse en ejercicio 6.

## Roles y permisos (ejercicio 5)

- `POST /usuarios` (ADMIN): `{nombre,email,password_provisoria,rol}`; rol inicial ADMIN o VENDEDOR. Crea personal con cambio obligatorio y evento en la misma transacción; no crea ficha de cliente ni devuelve hash.
- `GET /usuarios/{id}/roles` (ADMIN): historial completo, incluidas filas vencidas/revocadas. `POST` recibe `{rol,vence_en?}` con ADMIN/VENDEDOR/CLIENTE y fecha futura con zona; una asignación vigente repetida da 409. Reasignar una vencida cierra su fila y crea otra. `DELETE /usuarios/{id}/roles/{rol}` conserva historial y devuelve 200; no permite autorrevocar ADMIN ni dejar cero administradores vigentes (409).
- ADMIN administra catálogo y consulta `GET /eventos?page=1&size=20`. ADMIN o VENDEDOR administra clientes y registra/lista ventas. Los roles se consultan en DB en cada petición, sin confiar en los roles del token.
- `GET /mis-ventas` exige sólo autenticación y pagina únicamente ventas propias. El detalle `/ventas/{id}` admite personal o cliente dueño, incluso si éste ya no tiene rol CLIENTE; tercero 403, inexistente 404.
- `main.py` monta grupos público y protegido; este último tiene un único control de cambio obligatorio. Mientras está pendiente, rutas privadas devuelven 403, y `/auth` y catálogo público siguen disponibles. Cambiar contraseña habilita los permisos con la misma cookie.
- Los detalles de autor/editorial existentes siguen públicos por contener sólo catálogo. Todas las rutas de clientes/perfiles son privadas. Reposición y consulta de movimientos nuevas corresponden al próximo bloque de stock, todavía pendiente.
- El seed actual registra el evento `SISTEMA` / `Carga de los datos iniciales` dentro de su transacción. Sigue siendo el seed anterior de catálogo: aún no prepara los usuarios/roles y movimientos exigidos por el ejercicio 8. No usarlo para inicializar permisos ni ejecutarlo sobre una base con datos sin revisar su destino.

Verificación actual: **213 pruebas sin DB y 71 PostgreSQL**, incluyendo permisos, propiedad, historial, eventos y rollback. No se evalúan bloqueos de concurrencia del capítulo 7; la regla de administradores comprueba vigencia al momento de la operación.

## Dos proyectos para la entrega

- La raíz contiene el parcial durante el desarrollo. Al armar el zip se colocará en `parcial/`.
- [despliegue/](despliegue/PROCEDENCIA.md) conserva el TP original extraído del commit `54c7fa2e362904999e07857636bb97f087877341`. Su configuración y README originales se mantienen separados. Docker y VPS se agregan allí en los ejercicios 9 y 10.

No incluir `.env`, `.venv`, `__pycache__`, `tmp/` ni credenciales en el zip. El despliegue efectivo en VPS sigue pendiente; sólo se verificó en local.

## Preparación del parcial desde cero

Requisitos: Python 3.12 o superior y PostgreSQL 16 o superior. Los comandos siguientes se ejecutan desde la raíz, en PowerShell:

```powershell
py -3 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
Copy-Item env.example .env
& ./.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Editar localmente `.env`: completar usuario, contraseña y dirección de PostgreSQL, nombre de la base y `JWT_SECRET` con el valor generado. No publicar esa clave ni compartirla en capturas. La base debe existir antes de aplicar las migraciones.

| Variable | Uso |
|---|---|
| `POSTGRES_USER` | Usuario de PostgreSQL, obligatorio |
| `POSTGRES_PASSWORD` | Contraseña obligatoria, sin valor por defecto |
| `POSTGRES_DB` | Nombre de la base, obligatorio |
| `POSTGRES_HOST` | Host de PostgreSQL, obligatorio |
| `POSTGRES_PORT` | Puerto, por defecto 5432 |
| `JWT_SECRET` | Clave de firma obligatoria, sin valor por defecto; reservada para acceso en el siguiente bloque |
| `SQL_ECHO` | Mostrar consultas; por defecto false. También se admite el nombre anterior `ECHO_SQL` |
| `DB_POOL_SIZE` | Conexiones base del pool, por defecto 5, mínimo 1 |
| `DB_MAX_OVERFLOW` | Conexiones adicionales máximas, por defecto 10, mínimo 0 |
| `BCRYPT_ROUNDS` | Costo bcrypt, por defecto 12; rango admitido por bcrypt: 4 a 31 |
| `BCRYPT_CONCURRENCY` | Cantidad máxima de trabajos bcrypt simultáneos, por defecto 4, mínimo 1 |

`Settings` lee variables de proceso y `.env`, con prioridad para las primeras. Compone `database_url` mediante `@computed_field` y `URL.create`, preservando caracteres especiales de la contraseña. Las credenciales están ocultas en `repr` y en el texto de errores de validación. La URL calculada es interna: no imprimirla ni serializar Settings para respuestas o registros.

Si se viene del TP anterior, **`DATABASE_URL` ya no configura el parcial**. Separar sus datos en `POSTGRES_*` y agregar `JWT_SECRET`. El archivo `.env` real existente no fue modificado por la implementación. El TP preservado en `despliegue/` continúa usando su configuración original.

```powershell
& ./.venv/Scripts/python.exe -m alembic upgrade head
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

El esquema se crea exclusivamente con Alembic. Se conservan las dos migraciones del TP y se agregan `3e5d56535b0e` (tablas de acceso, movimientos, vínculo cliente/usuario e ISBN vigente) y `a05a50bc58a8` (trigger de sólo agregado). No usar `create_all`.

Los datos iniciales actuales siguen siendo los del TP. Solo en una base local de desarrollo que se pueda vaciar, después de confirmar su destino:

```powershell
& ./.venv/Scripts/python.exe seed.py
```

**`seed.py` borra los datos existentes antes de cargar.** No se ejecutó sobre ninguna base durante este bloque; todavía debe adaptarse al nuevo modelo del parcial.

## Ejecución y salud

API: `http://127.0.0.1:8000`; documentación interactiva: `http://127.0.0.1:8000/docs`.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

`/health/live` responde 200 sin tocar la base. `/health/ready` ejecuta `SELECT 1`: responde 200 si funciona y 503 con mensaje propio si falla.

El lifespan crea motor y fábrica de sesiones, guarda recursos en `app.state`, inicializa un semáforo bcrypt y calcula una sola vez el hash ficticio para el futuro login. bcrypt se ejecuta mediante `asyncio.to_thread`, conservando el cupo del semáforo hasta terminar incluso con cancelaciones. El motor se libera en `finally`, también ante errores. No se crea motor al importar módulos.

`get_session` obtiene la fábrica de `app.state`, entrega una sesión por petición y la cierra al salir; `expire_on_commit=False` conserva los atributos después de confirmar. Todavía no se agregaron los grupos de rutas de autorización: corresponden al bloque de acceso.

## Pruebas y límites de verificación

```powershell
& ./.venv/Scripts/python.exe -m pytest -q
```

La suite actual usa credenciales ficticias, motores sin conexiones y dobles controlados para salud. Incluye generación SQL offline de Alembic y fallos de configuración. No necesita PostgreSQL ni lee el `.env` real en sus pruebas de configuración. `pytest.ini` limita los tests a `test/` y mantiene temporales dentro de `tmp/`.

Se verificaron 158 pruebas de unidad/modelos/offline/HTTP y, por separado, 37 pruebas contra PostgreSQL 17 aislado. También se ejecutó desde una base vacía `upgrade head → downgrade base → upgrade head`, sin diferencias entre modelos y esquema según `alembic check`. Esto todavía no demuestra los casos HTTP C-01 a C-16 completos. Los archivos `.http` existentes y `test/evidencia_c07.md` corresponden al TP previo.

Para repetir la validación PostgreSQL completa con un Python convencional y los binarios instalados:

```powershell
& ./.venv/Scripts/python.exe scripts/test_postgres.py
# Otra instalación: agregar --pg-bin 'C:/ruta/PostgreSQL/bin'
```

El verificador crea un cluster nuevo dentro de `tmp/`, con datos ficticios, autenticación local de pruebas y escucha sólo en `127.0.0.1`, en un puerto libre distinto de 5432. Comprueba su directorio antes de usarlo, ejecuta las cuatro migraciones, la reversión a base y la nueva subida, compara el esquema, ejecuta las pruebas online y detiene su propio servidor en `finally`. No acepta una URL de una base existente ni lee el `.env` del proyecto. Logs y configuración temporal quedan ignorados en `tmp/`.

En esta sesión Codex/Windows, `initdb` requirió ejecución fuera del sandbox y el launcher `.venv` elevado presentó un fallo nativo al importar asyncpg. Se verificó el proceso completo con este arranque alternativo, que lee únicamente las dependencias ya instaladas en `.venv` y no modifica el Python global:

```powershell
& 'C:/Program Files/PostgreSQL/17/pgAdmin 4/python/python.exe' -c "import sys,runpy; from pathlib import Path; sys.path.insert(0,str(Path('.venv/Lib/site-packages').resolve())); runpy.run_path('scripts/test_postgres.py',run_name='__main__')"
```

La suite online se puede invocar explícitamente contra la configuración de un cluster temporal propio ya iniciado:

```powershell
& ./.venv/Scripts/python.exe -m pytest postgres_tests --postgres-config tmp/<cluster-propio>/connection.json -q
```

Sin ese archivo, con una configuración ajena o con el servidor caído, las pruebas online fallan; no se omiten simulando éxito. El cluster que genera el verificador ya está apagado al terminar, por lo que para repetir se vuelve a ejecutar el verificador completo.

En esta máquina se creó `.venv` desde Python 3.13.12 de pgAdmin mediante virtualenv, sin instalar paquetes en su entorno global. Se verificaron `sys.executable` y `sys.prefix` apuntando a `.venv`. En una máquina nueva se recomienda un Python completo con soporte para `venv` y los comandos anteriores.

## Estructura y reglas

`app/core/` contiene configuración, fábrica/sesiones, errores, paginación y la primitiva bcrypt; `app/main.py`, el lifespan y routers. `app/modules/usuarios/models.py` incorpora Usuario, AsignacionRol, IntentoAcceso y EventoSeguridad; MovimientoStock vive en libros. Cliente tiene usuario opcional escalar y Libro incorpora baja lógica e ISBN único sólo entre vigentes. El alta con stock positivo crea su movimiento inicial en la misma confirmación. La reposición, el descuento por ventas y la autorización completa siguen pendientes. `migrations/` contiene Alembic, `test/` las verificaciones sin DB y `postgres_tests/` las pruebas online.

Se mantienen nombres obligatorios de tablas/columnas, dinero con Decimal, handlers asincrónicos, precarga de relaciones y mensajes de error propios. El nuevo flujo Router → Service → UoW → Repository → Model y los cambios del modelo se aplicarán en los próximos bloques.

## Contratos y listados del ejercicio 3

Los ocho listados existentes usan `page` (desde 1) y `size` (1..100, por defecto 20), y responden `{items,total,page,size,pages}`. Esto reemplaza `limit`/`offset`; adaptar los clientes HTTP anteriores. Una colección vacía tiene una página; una página posterior a la última da 422. El total comparte filtros con los elementos, incluida la baja lógica y la búsqueda de título sin distinguir mayúsculas.

Las entradas rechazan campos extra. `PATCH /libros/{id}` admite solamente título y precio; aplica sólo campos enviados, rechaza null y no permite modificar stock. El alta usa `stock_inicial` y autorías (`autor_id`, `rol`, `orden`). `DELETE /libros/{id}` marca la baja y responde 204; detalle y catálogo dejan de devolverlo, sin romper ventas históricas. Las ventas rechazan renglones vacíos/repetidos y precios/totales enviados; el servidor calcula con Decimal. No hay PATCH de ventas.

**Integración pendiente con ejercicio 4:** `POST /libros/` requiere `requerir_usuario_id`, que por ahora responde 401 siempre. No hay usuario ficticio, ID enviado por cliente ni cabecera que evite el control. Al conectar cookie/usuario/roles, esa dependencia debe devolver el ID real; las pruebas ASGI/PostgreSQL ya sustituyen la dependencia por un usuario existente y verifican 201, movimiento inicial y rollback. Stock inicial cero no genera movimiento porque su cantidad no puede ser cero. El registro de usuarios y sus DTO se incorporarán junto con autenticación; no se afirma que ese criterio transversal ya está terminado.

La migración de servicios a repositorios/UoW corresponde al ejercicio 6. El contrato de stock inicial no significa que ya está resuelta toda la lógica de stock/ventas. Evidencia y límites en [progreso](docs/PROGRESO_PARCIAL_CAP1A6.md).

## Estado actual: ejercicio 8

Los apartados anteriores describen la evolución de los primeros ejercicios. Actualmente la autenticación, los permisos y el flujo Router → Service → UoW → Repository → Model están implementados. Todos los servicios usan UoW y repositorios; las ventas descuentan stock y guardan movimientos en la misma transacción. ADMIN puede reponer existencias y consultar su historial paginado. Los contratos y endpoints se documentan en [persistencia e inventario](docs/PERSISTENCIA.md).

El ejercicio 7 verifica integridad: el trigger rechaza UPDATE/DELETE directos de movimientos y los intentos de acceso se confirman en sesión/transacción independientes del rollback de petición. Incluye [SQL C-14](test/solo_agregado.sql), [transcript psql real](evidencia/c14_psql.txt) y [casos, resultados e instrucciones de repetición](evidencia/ej7_integridad.md). Las regresiones comprueban intentos fallidos y exitosos con fallo posterior, observados desde otra sesión, mientras una escritura testigo revierte. El verificador PostgreSQL también localiza y ejecuta `psql` de esa instalación; el script exige un `movimiento_id` existente y no usa IDs ni conexiones reales por defecto.

El ejercicio 8 verifica precarga sin N+1 y comprobantes con `BackgroundTasks`. C-15 compara ventas de dos y cuatro renglones con sesiones nuevas, incluido un libro dado de baja, y demuestra que la serialización no necesita sesión ni consultas adicionales. Consultas reales y reproducción en [evidencia de lecturas](evidencia/ej8_lecturas.md).

El comprobante se agenda sólo después de confirmar la venta y se ejecuta después del último cuerpo de respuesta ASGI. Las pruebas cubren 201, rechazo 409 y fallos de escritura/commit; sólo las ventas confirmadas generan aviso. La espera de 0.5 segundos es cooperativa (`asyncio.sleep`), y el mensaje aparece con el arranque normal de uvicorn: [log real e instrucciones](evidencia/ej8_comprobante.md). La tarea recibe identificador, correo y total como escalares; no conserva sesión ni entidades ORM. `BackgroundTasks` puede perder el aviso si termina el proceso y no proporciona reintentos ni entrega durable.

El seed ampliado y los materiales restantes de entrega siguen pendientes. Docker del TP y simulación local del punto 10 están verificados; el VPS efectivo queda pendiente. Concurrencia del capítulo 7 y Redis del capítulo 8 están excluidos de este parcial.
