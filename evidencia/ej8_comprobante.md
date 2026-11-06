# Comprobante con uvicorn normal

La ejecución real registrada en [ej8_uvicorn.txt](ej8_uvicorn.txt) verifica ventas
de cantidades 1 y 2. En ambos casos, la línea HTTP `201 Created` precede al mensaje
de `libreria.ventas`, que incluye identificador, destinatario y total. No se usa
una configuración especial de logging ni se sustituye el emisor por un mock.

## Repetición

Desde la raíz, con las dependencias de desarrollo y PostgreSQL instalado:

```powershell
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe scripts/test_postgres.py
```

El runner crea un cluster nuevo y aplica las migraciones. La suite incluye
`postgres_tests/test_uvicorn_receipt.py`, que arranca dos procesos con el comando
normal `python -m uvicorn app.main:app --host 127.0.0.1 --port <puerto-libre>`.
Cada proceso trabaja desde un directorio temporal, con variables del cluster
de pruebas y una clave JWT ficticia; no se usa el `.env` del proyecto.

La prueba espera `/health/ready`, autentica un ADMIN de prueba y crea un libro y
una venta por HTTP. Comprueba una única línea de comprobante y su posición
posterior a la línea de respuesta. Las pruebas de ASGI complementarias verifican
el orden respecto del último cuerpo de respuesta y el commit; una línea de access
log por sí sola no prueba el envío del último cuerpo.

Los logs completos se conservan en el directorio que imprime el runner, bajo
`pytest-online/test_comprobante_visible_con_u*/uvicorn.log`. La limpieza termina
los procesos propios de uvicorn en `finally`; el runner detiene PostgreSQL.

## Límite aceptado

`BackgroundTasks` se ejecuta en el mismo proceso después de enviar la respuesta.
El aviso es simulado y puede perderse si el proceso termina: no hay cola durable,
reintentos ni garantía de entrega. Redis no forma parte de este ejercicio.
