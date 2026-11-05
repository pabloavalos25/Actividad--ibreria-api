# Plan del parcial — capítulos 1 a 6

Fuente: `docs/Parcial_Cap1a6_Consigna.pdf` (24 páginas). Revisión inicial del 5 de noviembre de 2026. Este documento organiza el trabajo; no representa una implementación ni una validación aprobada.

La lectura completa posterior está documentada en [REQUISITOS_PARCIAL_CAP1A6.md](REQUISITOS_PARCIAL_CAP1A6.md): son diez ejercicios (1–8 del parcial, 9–10 de Docker/VPS). Esa matriz detalla los criterios de aceptación que este plan resume.

El estado de implementación y las verificaciones de cada bloque se registran en [PROGRESO_PARCIAL_CAP1A6.md](PROGRESO_PARCIAL_CAP1A6.md).

## Entrega y alcance obligatorio

La entrega es grupal, en `Parcial_Cap1a6_<NombreDelGrupo>.zip`, con dos proyectos separados:

- `parcial/`: ampliación del TP con acceso, roles, repositorios, Unit of Work, integridad y pruebas.
- `despliegue/`: TP de capítulos 1 a 4 tal como se entregó, con Docker y documentación/evidencia del VPS. No debe incorporar las modificaciones funcionales del parcial.

Excluir `.env`, `.venv` y `__pycache__` de ambas carpetas. No incluir secretos. La fecha de entrega se publica en el campus. El VPS debe seguir accesible hasta la publicación de las notas. No se evalúan bloqueos de concurrencia del capítulo 7 ni colas Redis del capítulo 8.

## Requisitos principales

| Área | Obligatorio |
|---|---|
| Configuración y ciclo de vida | `Settings` con pydantic-settings; URL mediante `@computed_field` y variables `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`. Contraseña y clave de firma sin valores por defecto. Motor, pool configurable, fábrica de sesiones y hash ficticio creados en lifespan; `expire_on_commit=False`; cierre con `dispose()`. Health live sin consultar DB y ready con `SELECT 1`, 503 si falla. |
| Modelo y migraciones | Nuevas tablas `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `movimiento_stock`; `cliente.usuario_id` nullable y UNIQUE; `libro.borrado_en`. Índices únicos parciales para ISBN vigente y asignación no revocada. Nuevas fechas con zona e índices para nuevas FK. Dos migraciones adicionales: tercera autogenerada y revisada; cuarta manual para trigger de sólo agregado. |
| Contratos y listados | DTO separados, `extra="forbid"`, PATCH parcial, errores propios. Listados `{items,total,page,size,pages}`; página inexistente y tamaño inválido: 422. `stock` no puede modificarse con PATCH. |
| Acceso | bcrypt fuera del bucle de eventos y con semáforo; hash ficticio para correos inexistentes. Token firmado PyJWT únicamente en cookie HttpOnly, SameSite=Lax y Max-Age; no en cuerpo ni recibido desde Authorization. Registro atómico de usuario, rol CLIENTE y cliente; correo de cliente existente: 409 sin apropiarse de su ficha. |
| Login y limitación | Mismo cuerpo 401 y tiempo parecido con correo inexistente o contraseña incorrecta. Cinco fallos para un correo/IP en 60 segundos: siguiente intento 429 con Retry-After sin verificar contraseña. Un éxito reinicia el conteo sin borrar historial. Intentos persistidos en sesión propia, sobreviviendo al rollback del login. |
| Autorización | ADMIN, VENDEDOR y CLIENTE mediante asignaciones históricas con vigencia consultadas en DB en cada petición. Token no decide permisos. Sin sesión: 401; sin permiso: 403. No autorrevocación de ADMIN ni dejar cero administradores vigentes. Vencimiento pasado o sin zona: 422. Cambio obligatorio bloquea rutas protegidas, permite `/auth` y públicas; al cambiar, la misma cookie sigue sirviendo. |
| Propiedad y auditoría | `/mis-ventas` para autenticados; detalle de venta para personal o cliente dueño, 403 para terceros. No exigir rol de personal al dueño. Alta de personal, cambios de rol y contraseña generan evento en la misma transacción. |
| Repositorios y UoW | Router → Service → UoW → Repository → Model. `BaseRepository[T]`, `SoftDeleteRepository[T]`, repositorios y UoW por módulo. Repositorios hacen flush, nunca commit; precargan relaciones. Router construye UoW; servicio lo recibe y abre; UoW confirma/revierte sin cerrar sesión. |
| Stock y ventas | Punto único de escritura: alta con `stock_inicial`, reposición y ventas producen movimientos. `cantidad` de movimiento distinta de cero y tabla protegida contra UPDATE/DELETE mediante trigger. Venta con al menos un renglón, sin libros repetidos, precios copiados y total Decimal calculado en servidor; stock, movimientos, venta y renglones atómicos. Stock insuficiente: 409 sin escrituras parciales. |
| Borrado lógico | Libro dado de baja no aparece en catálogo ni puede venderse/reponerse; ventas anteriores conservan su información. El ISBN puede reutilizarse, con un solo libro vigente. |
| Docker y VPS | Sobre copia preservada del TP: `python:3.12-alpine`, usuario sin privilegios, sin secretos, migraciones al arrancar y HEALTHCHECK con `127.0.0.1`. `docker run` con `--env-file` externo, puerto asignado y `--restart unless-stopped`. PostgreSQL del servidor, no dentro del contenedor. `DEPLOY.md` con URL, fecha/hora, comandos completos sin secretos, cambios y actualización. |

La estructura pide además `app/core/security.py`, `dependencies.py`, `repository.py`, `paginacion.py`, `unit_of_work.py` y módulo `usuarios`. El detalle de cada ejercicio debe releerse antes de implementar: esta síntesis no sustituye la consigna.

## Brechas verificadas en el repositorio

- El README y `docs/ROADMAP.md` corresponden al TP 1 a 4, marcado como terminado; no son todavía el plan del parcial.
- El árbol actual no incluye módulo usuarios, repositorios, UoW, seguridad, paginación nueva ni archivos Docker de entrega.
- `app/modules/libros/service.py` recibe `AsyncSession`, confirma directamente y pagina con limit/offset. Su PATCH aplica los campos del DTO sin la nueva política de movimientos.
- `app/modules/ventas/service.py` confirma directamente y calcula precios/total, pero no descuenta stock ni registra movimientos.
- `app/main.py` ya crea motor/fábrica en lifespan y hace dispose al apagar; aún no incorpora usuarios ni separación de rutas o hash ficticio.
- `requirements.txt` no incluye pydantic-settings, bcrypt, PyJWT ni un runner automatizado. `test/` contiene casos HTTP y evidencia del TP anterior.
- `openspec list --json` no pudo ejecutarse: CLI no disponible. No se encontraron skills OpenSpec en las ubicaciones revisadas; no se creó estructura ni se supuso estado OPSX.
- Se encontró Python en el entorno de pgAdmin, pero sin dependencias de la aplicación ni pytest. No se ejecutó baseline y no se afirma que las pruebas actuales pasen.

## Orden de trabajo propuesto

1. Preservar una copia trazable del TP 1 a 4 para `despliegue/`, excluyendo secretos y archivos generados. Resolver la ubicación de trabajo y preparar un entorno Python aislado con runner, sin modificar el Python global de pgAdmin.
2. Implementar el ejercicio 1 mediante TDD: Settings, construcción segura de URL, validación de secretos, pool y ciclo de vida. Verificar health y cierre de recursos.
3. Agregar modelos y las dos migraciones requeridas. Revisar SQL antes de aplicar; validar upgrade → downgrade base → upgrade en una base de pruebas aislada.
4. Crear repositorios/UoW y migrar módulos por bloques; luego envoltorio de paginación y contratos estrictos.
5. Implementar registro/login/cookie, limitación y persistencia de intentos; luego roles, cambio obligatorio, propiedad y auditoría.
6. Implementar movimientos, venta atómica, reposición y baja lógica; adaptar seed y comprobar stock = suma de movimientos.
7. Completar casos C-01 a C-16, evidencia C-14/C-15 y README del parcial. Preparar Docker del TP preservado y casos D-01 a D-08 cuando estén disponibles los datos del VPS.

Cada cambio de producción debe seguir baseline → RED → GREEN → triangulación (mínimo dos casos por comportamiento) → refactor, con evidencia. Si falla la baseline, informar el fallo preexistente antes de continuar.

## Aprobación concreta antes de escribir configuración o seguridad

**Aprobación: aprobada por el usuario el 5 de noviembre de 2026**, mediante respuesta «si» a la consulta sobre configuración, migraciones, autenticación, roles y auditoría detalladas en este plan. El alcance local siguiente está autorizado; no se debe solicitar nuevamente esta aprobación.

La gobernanza proporcionada clasifica autenticación, autorización y auditoría como CRITICAL, y configuración que afecta datos como HIGH. Se requiere aprobación expresa para:

- Sustituir la configuración del parcial por Settings con variables PostgreSQL separadas y clave JWT obligatoria, sin secretos por defecto; adaptar lifespan y configuración de migraciones sin modificar ni publicar credenciales reales.
- Agregar las tablas/migraciones de acceso y auditoría; implementar bcrypt asíncrono mediante ejecución fuera del bucle y semáforo, JWT por cookie y hash ficticio.
- Agregar registro/login/logout, consulta de sesión y cambio de contraseña; límites de acceso persistidos, roles consultados en DB, reglas de ADMIN, protección de rutas y acceso a ventas propias.
- Registrar los eventos de seguridad dentro de la transacción del cambio y mantener los intentos de acceso en una transacción independiente según la consigna.

La aprobación habilita implementar y probar esos cambios en el proyecto y en una base de pruebas aislada. El despliegue efectivo y el borrado/carga de datos en el VPS requieren los datos del servidor y autorización para esas operaciones concretas. No se ejecutará `seed.py` sobre una base con datos sin confirmar su destino.

## Pendientes que no deben inventarse

- La lectura completa confirmó `access_token` y el máximo de 72 bytes UTF-8 para contraseñas; algoritmo, duración, mínimo de contraseña y límite del semáforo no tienen valores obligatorios en la consigna. Elegirlos y documentarlos al implementar, sin tratar los ejemplos como requisitos.
- El TP original ya fue preservado en `despliegue/` desde el commit `54c7fa2e362904999e07857636bb97f087877341`, con procedencia registrada y contenido verificado. Falta empaquetar la versión ampliada como `parcial/` para la entrega final; durante el desarrollo permanece en la raíz.
- Datos de acceso, host de PostgreSQL, puerto asignado y URL del VPS; fecha límite del campus.
- OpenSpec continúa sin estar disponible. Ya funcionan el entorno Python aislado y las pruebas PostgreSQL en un clúster temporal propio. Los ejercicios 1 y 2 tienen verificaciones registradas en el documento de progreso; las verificaciones funcionales de los ejercicios siguientes permanecen pendientes.
