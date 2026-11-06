# Persistencia del parcial

Cada servicio recibe un UoW creado por la dependencia de su módulo. El UoW adopta la transacción de lectura de la petición, confirma al salir normalmente y revierte ante error, incluso error al confirmar. No cierra la sesión: eso corresponde a `get_session`.

`BaseRepository(session, model)` concentra lectura, altas y cambios: `add`/`update` sincronizan con flush pero no confirman. `SoftDeleteRepository` agrega filtrado y baja lógica, sin introducir esos métodos en la base.

Antes de generar un hash, `terminar_lectura` finaliza la lectura iniciada por autenticación; rechaza hacerlo si hay cambios pendientes para evitar descartarlos. Los repositorios declaran la precarga de cada lectura relacionada.

Los módulos autores, editoriales, géneros, clientes, usuarios, libros y ventas componen sus repositorios sobre la misma sesión de petición. FastAPI reutiliza `get_session` tanto para autenticar como para construir el UoW del servicio. Los servicios no ejecutan SQL ni manipulan la sesión directamente; las consultas, filtros y precargas pertenecen a los repositorios.

La única excepción de escritura independiente es `HistorialAcceso`: abre su propia sesión y confirma los intentos de login. Así un intento fallido permanece aunque el 401 revierta la operación principal, y puede aplicarse el límite de intentos. No usar esta excepción para escrituras de negocio.

## Inventario y ventas

`modificar_stock` es el punto compartido de modificación de existencias. Alta, reposición y venta lo llaman dentro de su UoW y aportan el actor real. Cada cambio no nulo guarda un movimiento; una venta también aporta su ID. Un alta con stock cero no genera un movimiento cero.

- `POST /libros/{libro_id}/reponer`: requiere ADMIN y cuerpo `{"cantidad": 2, "motivo": "Compra"}`. Devuelve el detalle actualizado. Cantidades no positivas dan 422; un libro dado de baja da 409 y uno inexistente 404.
- `GET /libros/{libro_id}/movimientos?page=1&size=20`: requiere ADMIN y devuelve `items`, `total`, `page`, `size` y `pages`. Conserva acceso al historial de libros dados de baja. Cada elemento incluye actor (`usuario_id`), cantidad, motivo, fecha y venta opcional.
- `POST /ventas/`: valida todos los renglones, copia sus precios Decimal y confirma venta, renglones, descuentos y movimientos juntos. Un libro ausente, borrado o sin stock suficiente, o un cliente inexistente, devuelve 409. Un fallo posterior de escritura revierte toda la operación.

La baja de un libro no borra ventas ni movimientos y permite reutilizar su ISBN, que sigue siendo único entre libros vigentes. Los repositorios precargan las relaciones de salida antes de confirmar. El UoW traduce conflictos de integridad a 409 y desbordes de datos a 422 sin exponer SQL.

Para libros creados por API, el stock coincide con la suma de movimientos. Los datos heredados del seed o fixtures no reconstruyen movimientos históricos. La protección frente a ventas simultáneas queda fuera del alcance evaluado; el ejercicio 7 corresponde a integridad, no a bloqueos de concurrencia.

## Contrato de lectura sin N+1

Las relaciones que forman parte de cada DTO se precargan en su repositorio. El detalle de venta obtiene cliente y renglones/libros en dos SELECT, incluidos libros dados de baja. El conteo no crece al pasar de dos a cuatro renglones; la petición autenticada observada agrega una consulta de usuario y otra de roles. Sus listados paginados agregan el total. No se precargan relaciones que no integran la salida.

Libros cargan editorial y género en catálogo, y además autorías/autor en detalle. Los libros por autor cargan el libro de cada autoría; clientes cargan su perfil opcional. Las pruebas construyen los DTO después de cerrar sesiones nuevas: serializar no puede emitir SQL ni depender de lazy loading. Evidencia y reproducción en [ej8_lecturas.md](../evidencia/ej8_lecturas.md).

## Verificación reproducible

Ejecutar `.venv/Scripts/python.exe -m pytest -q` y `.venv/Scripts/python.exe scripts/test_postgres.py`. El segundo crea un cluster nuevo en `tmp/`, verifica upgrade/check/downgrade/upgrade y ejecuta las pruebas PostgreSQL; lo detiene al terminar y conserva los logs. No usa `.env` ni la base habitual.
