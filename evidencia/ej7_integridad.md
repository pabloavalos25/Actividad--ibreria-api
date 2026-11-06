# Ejercicio 7: integridad

## Alcance y destino

Verificación del 5 de noviembre de 2026 sobre PostgreSQL 17 temporal propio,
creado por `scripts/test_postgres.py`, con escucha en `127.0.0.1` y puerto
distinto de 5432. No se usaron `.env`, VPS ni bases existentes. Los usuarios,
libros e intentos son datos ficticios de las fixtures, no el seed ampliado.
El ejercicio 7 es integridad; el 8 corresponde a precarga y asincronía.

## C-14: UPDATE y DELETE directos

`test/solo_agregado.sql` recibe un `movimiento_id` existente explícito. Muestra
la fila original, intenta un UPDATE sin cambios y un DELETE dentro de
savepoints, exige SQLSTATE **23514** para cada rechazo y compara la fila
completa antes/después. Termina con ROLLBACK. Si falta el identificador, no
existe la fila, se acepta un cambio o se produce otro error, el proceso falla.
No basta imprimir un error para aprobar la verificación.

Repetición segura, creando un cluster nuevo y deteniéndolo automáticamente:

```powershell
$env:PYTHONIOENCODING='utf-8'
& ./.venv/Scripts/python.exe scripts/test_postgres.py
```

Las pruebas localizan `psql` mediante el `BINDIR` del servidor temporal y
validan `SHOW data_directory` y la base antes de insertar fixtures o limpiar.
Prueban cantidades +3 y -1; INSERT está permitido. La cobertura asyncpg
comprueba UPDATE que cambia el motivo, UPDATE sin cambios y DELETE, para
ambos signos. Tras cada rechazo conserva cantidad y motivo originales.

Para ejecutar sólo el SQL en un destino de desarrollo **ya confirmado**, elegir
una fila real con `SELECT id, cantidad, motivo FROM movimiento_stock` y usar
host, puerto, usuario y base de ese destino; no copiar el puerto temporal de
una ejecución pasada ni asumir que el ID 1 existe:

```powershell
& 'C:/Program Files/PostgreSQL/17/bin/psql.exe' -X --no-password -h HOST_CONFIRMADO -p PUERTO_CONFIRMADO -U USUARIO -d BASE_CONFIRMADA -v movimiento_id=ID_EXISTENTE -f test/solo_agregado.sql
```

Si la conexión requiere contraseña, usar la configuración segura propia de
psql, sin escribirla en el comando ni en este documento. El SQL no administra
credenciales o permisos PostgreSQL. La comprobación falla si la fila no existe,
porque un trigger por fila no se ejecuta sobre una sentencia sin coincidencias.

El transcript real se conserva en [c14_psql.txt](c14_psql.txt). Los errores de
ambos comandos son esperados; psql sale 0 únicamente cuando verificó los dos
rechazos y la integridad de la fila. Como control negativo, la prueba deshabilita
temporalmente el trigger **sólo en el cluster propio**: UPDATE pasa con estado
00000, el verificador falla con salida 3 y la conexión revierte su transacción.
Un `finally` vuelve a habilitar el trigger y limpia las fixtures.

Se detectó durante RED/GREEN que psql 17 ignora el argumento de `\quit 3` y
devuelve 0. La versión final usa una excepción SQL con `ON_ERROR_STOP` para
que el control negativo produzca un fallo real.

## Intentos de acceso independientes

`test_intento_independiente_sobrevive_rollback_peticion` ejercita `/auth/login`
con contraseña incorrecta (401 real) y correcta con error inyectado en la
consulta posterior de roles. En ambos casos:

- La dependencia de petición inserta y hace flush de un evento testigo.
- Se observan objetos `AsyncSession` distintos para petición e historial y se
  comparan sus `txid_current()`, que también deben ser distintos.
- Una tercera sesión comprueba exactamente un intento con el email/IP y el
  resultado esperado; no encuentra el evento testigo revertido.

La variante incorrecta conserva el cuerpo público 401. La correcta verifica
la contraseña, confirma el intento exitoso y falla antes del commit de la
petición. Esto demuestra independencia; contar intentos sin una escritura
revertida ni una sesión observadora no bastaría.

No fue necesario cambiar `HistorialAcceso`: ya usa sesión/transacción propias.
Su comentario documenta que es la única escritura independiente, que el 401
revierte la petición y que el costo es conservar filas de peticiones fallidas.
La limitación, el reinicio por éxito y la conservación del historial siguen
cubiertos por las pruebas existentes.

## Resultados

La baseline fue **236/236** sin DB (6.62 s) y **83/83** PostgreSQL (22.83 s).
El cluster baseline `postgres-tests-4ac36b0dc713`, puerto 63654, quedó detenido.
La primera pasada de C-14 falló por el archivo SQL ausente (4 fallos). Después
de crear el SQL, dos casos positivos pasaron y el control negativo descubrió
el comportamiento de `\quit`; tras corregirlo, pasaron los cuatro casos de
psql y los dos de aislamiento (**6/6**, 3.62 s).

La verificación final completa pasó **236/236** sin DB (11.91 s) y **91/91**
PostgreSQL (25.75 s), en el cluster nuevo `postgres-tests-07f6fd0b12e6`, puerto
52166, detenido al terminar y sin `postmaster.pid`. Upgrade head, downgrade
base y nuevo upgrade head/check no dejaron drift ni restos en base. Las doce
pruebas focalizadas previas pasaron en 3.64 s. Los logs íntegros de cada
cluster se conservan localmente en `tmp/<cluster>/verification.log`.

Los ciclos de migraciones y el apagado del cluster también se registran en la sección de ejercicio 7 de
[progreso](../docs/PROGRESO_PARCIAL_CAP1A6.md) y en el `verification.md` local
del cambio OpenSpec. No se atribuye RED nuevo al trigger ni a `HistorialAcceso`,
que ya existían y pasaron las regresiones nuevas sin cambios de producción.
