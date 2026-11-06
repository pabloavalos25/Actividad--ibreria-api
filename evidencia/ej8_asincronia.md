# Orden de respuesta y asincronía del ejercicio 8

La regresión `postgres_tests/test_receipt_order.py` usa PostgreSQL y el UoW
reales. Observa el retorno del commit, la agenda de `BackgroundTasks`, el envío
del último `http.response.body` y la entrada a la tarea. Para cantidades 1 y 2
el orden es exactamente `commit → schedule → body → receipt`, una única vez.
El aviso recibe sólo ID, correo y total, coincidentes con la respuesta.

Stock insuficiente (409), una excepción después del flush del movimiento y un
fallo de commit no agendan avisos y dejan cero ventas. Sólo el emisor se sustituye
por un observador en esta prueba; la prueba de uvicorn ejecuta el emisor real.
HTTPX espera las tareas de fondo antes de devolver el control al test: su duración
no se usa como demostración del orden de respuesta.

`test/test_async_receipt.py` intercepta la espera mediante una coroutine
controlada. Exige un único `await sleep(0.5)`, permite avanzar a otra tarea antes
de liberar la espera y comprueba ausencia de log antes y un mensaje exacto
después. Usa dos ventas/destinatarios/totales distintos. El objetivo es comprobar
cooperación y orden sin umbrales de tiempo frágiles; la espera real se ejecuta
además en las pruebas con uvicorn.

## Auditoría de handlers

La revisión del árbol actual encontró **40/40 handlers propios `async def`**.
Se recorrieron los routers incluidos recursivamente (FastAPI utiliza
`original_router` para las inclusiones); no se contaron rutas internas de docs.
La revisión de `app/` no encontró `time.sleep`, llamadas a `requests` ni
subprocesos bloqueantes. Se revisaron también los servicios y repositorios:
la E/S de PostgreSQL es asíncrona y bcrypt se ejecuta con `asyncio.to_thread`
bajo semáforo. Las dependencias síncronas triviales que construyen UoW no son
handlers ni realizan E/S. Esta auditoría es inspección de código, no una prueba
exhaustiva de rendimiento para toda futura llamada añadida a la aplicación.

## Repetición

```powershell
.venv/Scripts/python.exe -m pytest -q test/test_async_receipt.py
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe scripts/test_postgres.py
```

El runner crea y detiene su cluster propio; los datos son ficticios. El detalle
del proceso real y sus logs está en [ej8_comprobante.md](ej8_comprobante.md).
No se cambió producción ni migraciones: el comportamiento existente pasó las
regresiones nuevas desde la primera ejecución. No se atribuye un RED retrospectivo.
