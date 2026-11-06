# Ejercicio 10: simulación local

Ejecución realizada el 6 de noviembre de 2026 en Docker Desktop 29.9.2. Esta evidencia corresponde a una simulación local y no acredita acceso público ni disponibilidad de un VPS.

Comando reproducible desde la raíz, con Docker y PostgreSQL 17 instalados:

```powershell
./.venv/Scripts/python.exe scripts/test_docker.py --point10
```

El runner crea un clúster PostgreSQL temporal vacío, un archivo de entorno fuera del contexto de build y nombres únicos de contenedor e imagen. Ejecuta migraciones, carga `despliegue/seed.py` únicamente en esa base vacía y consulta la API desde el host por `127.0.0.1`. No acepta una URL existente ni inspecciona el `.env` habitual.

Resultados observados:

- D-02 local: el primer inicio aplicó las dos migraciones y `/health/ready` respondió 200.
- D-03 local: el catálogo respondió 200; la venta de 2 Rayuelas respondió 201, venta #3, total `50000.00`.
- D-04 local: al detener y recrear el contenedor, la venta #3 permaneció y no se repitieron las migraciones.
- D-08 local: el log mostró el comprobante #3 después del 201.
- Salud: al detener PostgreSQL, readiness respondió 503 y Docker pasó a `unhealthy`; después de recuperar la base volvió a `healthy`.
- Limpieza: los contenedores e imagen propios se eliminaron y el clúster temporal se detuvo.

La salida íntegra sanitizada está en [vps_local_simulation.txt](vps_local_simulation.txt). La URL local y puertos efímeros aparecen allí como datos de ejecución local. D-02/D-03/D-04/D-08 en un VPS siguen pendientes.
