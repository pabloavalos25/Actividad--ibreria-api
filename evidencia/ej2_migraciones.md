# Ejercicio 2 — evidencia de modelos y migraciones

Fecha: 2026-11-05. PostgreSQL 17.10. Datos y credenciales ficticios; ningún acceso al PostgreSQL habitual del puerto 5432 ni a la base libreria.

## Baseline y generación real

1. `python -m pytest -q`: **36 passed** antes de modificar modelos.
2. Cluster temporal propio `tmp/postgres-ej2/data`, `127.0.0.1:10628`; `SHOW data_directory` confirmó la ruta exacta. Base nueva `parcial_ej2`.
3. `alembic upgrade head` aplicó únicamente `846f445b2248` y `332ba12e013b`; `alembic check`: **No new upgrade operations detected**.
4. RED modelos: **ImportError de MovimientoStock**. Después, 8 tests de relaciones verdes.
5. RED SQL: **12 fallos por esquema nuevo inexistente** sobre la base con sólo las dos migraciones del TP.
6. `alembic revision --autogenerate -m acceso_y_movimientos_stock` generó realmente `3e5d56535b0e_acceso_y_movimientos_stock.py`.

Salida relevante de autogenerate:

```text
Detected added table 'evento_seguridad'
Detected added table 'intento_acceso'
Detected added table 'usuario'
Detected added table 'asignacion_rol'
Detected added table 'movimiento_stock'
Detected added column 'cliente.usuario_id'
Detected added column 'libro.borrado_en'
Detected removed unique constraint 'uq_libro_isbn' on 'libro'
Detected added index 'uq_libro_isbn_vigente' on '('isbn',)'
```

Se leyó la revisión antes de aplicarla. El generador omitió el import de AutoString y dejó `drop_constraint(None)` para la FK nueva de cliente. Se corrigió a String SQLAlchemy equivalente y FK nombrada en upgrade/downgrade; el comentario de la revisión describe ambos ajustes. La copia sin corregir queda como temporal ignorado `tmp/postgres-ej2/generated_revision.raw.py`.

## Cuarta revisión manual y RED/GREEN

`alembic revision -m movimiento_stock_solo_agregado` creó el archivo de revisión vacío; se escribió manualmente función PL/pgSQL y trigger en `a05a50bc58a8_movimiento_stock_solo_agregado.py`.

Antes: **4 failed — DID NOT RAISE CheckViolationError** para UPDATE/DELETE con movimientos positivos y negativos. Después: ambos comandos rechazados, conservando la fila original; INSERT permitido. La suite PostgreSQL ampliada terminó con **29 passed**.

## Ciclo final desde cluster nuevo

Verificador: `scripts/test_postgres.py`. En esta sesión se usó el launcher:

```powershell
& 'C:/Program Files/PostgreSQL/17/pgAdmin 4/python/python.exe' -c "import sys,runpy; from pathlib import Path; sys.path.insert(0,str(Path('.venv/Lib/site-packages').resolve())); runpy.run_path('scripts/test_postgres.py',run_name='__main__')"
```

Se ejecutó fuera del sandbox con aprobación porque initdb necesita crear su proceso con otro token. Las dependencias permanecen dentro de `.venv`. El Python embebido requiere bootstrap sys.path también en hijos; no se instaló ni configuró nada global.

Destino real: `tmp/postgres-tests-5f79da9ca16f/data`, escucha `127.0.0.1:52783`, base `parcial_ej2` y usuario `parcial_test` del cluster nuevo.

Salida significativa:

```text
Running upgrade  -> 846f445b2248
Running upgrade 846f445b2248 -> 332ba12e013b
Running upgrade 332ba12e013b -> 3e5d56535b0e
Running upgrade 3e5d56535b0e -> a05a50bc58a8
No new upgrade operations detected.
Running downgrade a05a50bc58a8 -> 3e5d56535b0e
Running downgrade 3e5d56535b0e -> 332ba12e013b
Running downgrade 332ba12e013b -> 846f445b2248
Running downgrade 846f445b2248 ->
Downgrade base: sin tablas de dominio ni función de sólo agregado
Running upgrade  -> 846f445b2248
Running upgrade 846f445b2248 -> 332ba12e013b
Running upgrade 332ba12e013b -> 3e5d56535b0e
Running upgrade 3e5d56535b0e -> a05a50bc58a8
No new upgrade operations detected.
29 passed, 1 warning in 2.22s
waiting for server to shut down..... done
server stopped
```

El aviso correspondió a caché pytest compartida no escribible; se redirigió posteriormente al temporal propio. No afectó los resultados. Logs completos ignorados: `verification.log` y `server.log` en la carpeta temporal anterior.

También se verificaron **44 pruebas sin DB** y una revisión independiente confirmó **44 + 29**, sin omisiones. Imports frescos `app.main`, `seed` y `configure_mappers()` correctos, sin ejecutar seed.

Los clusters propios de puertos 10628 y 33873 se detuvieron antes del fresh-run final; el puerto 52783 fue detenido por el finally del verificador. Un intento inicial con pg_ctl heredando PIPE se abortó de forma segura y se reemplazó por archivos de log: no cuenta como ejecución exitosa.

Esto es evidencia del ejercicio 2. La captura psql C-14 con el seed completo y los casos HTTP de los siguientes ejercicios siguen pendientes; no se presentan aquí como aprobados.
