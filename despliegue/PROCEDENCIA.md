# Procedencia del TP

Copia de los archivos versionados del TP de capítulos 1 a 4, extraída con `git archive` del commit `54c7fa2e362904999e07857636bb97f087877341` el 5 de noviembre de 2026, antes de modificar el parcial.

No se copiaron `.env`, `.venv`, `.git` ni archivos locales no versionados. Los archivos originales se conservan en la raíz, que se utiliza como proyecto parcial durante el desarrollo; al empaquetar la entrega se colocarán en `parcial/`.

El ejercicio 9 agrega Dockerfile, exclusiones de contexto, arranque y salud, ejemplo de entorno y documentación de contenedor. Los archivos funcionales originales (`app/`, migraciones, requirements, configuración Alembic y seed) se verifican contra este commit mediante `test/test_tp_provenance.py`, normalizando únicamente saltos de línea. No se ejecutaron migraciones ni seed sobre el VPS; su configuración y despliegue corresponden al ejercicio 10.
