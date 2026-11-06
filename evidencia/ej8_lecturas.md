# Ejercicio 8: lecturas y evidencia C-15

La prueba `postgres_tests/test_read_queries.py` mide sentencias SELECT reales con un listener de SQLAlchemy sobre el motor PostgreSQL de un cluster nuevo de pruebas. No usa `.env`, datos externos ni overrides de autenticación. Las ventas de prueba se preparan fuera de la ventana medida; el login también queda fuera del contador.

## Resultado observado

| Renglones | Repositorio de detalle | Petición HTTP autenticada | Serialización sin sesión |
|---|---:|---:|---:|
| 2 | 2 SELECT | 4 SELECT | 0 SELECT |
| 4 | 2 SELECT | 4 SELECT | 0 SELECT |

La petición incluye una lectura de usuario, una de roles y las dos de detalle (venta/cliente y renglones/libros). La igualdad entre tamaños es el contrato; cuatro no es un límite universal para otros endpoints o futuras dependencias. Las consultas exactas medidas están en [c15_consultas.txt](c15_consultas.txt), sin valores de parámetros.

Cada lectura de repositorio empieza con una sesión nueva y un identity map vacío. La sesión se cierra antes de construir y serializar el DTO. Los dos tamaños contienen un libro dado de baja después de vender: su título sigue incluido. La respuesta HTTP coincide con el DTO de la lectura aislada.

Se cubren además listados de ventas generales, por cliente y por usuario (tres SELECT: total, venta/cliente y renglones/libros). La serialización posterior al cierre conserva todos los renglones. Otros dos casos verifican libro con editorial, género opcional y autoría/autor; catálogo y filtros editorial/género; libros por autor; cliente con y sin perfil. En todos se serializa tras cerrar su propia sesión, sin emitir SQL adicional.

## Reproducción

Desde la raíz, con las dependencias de `requirements-dev.txt` y PostgreSQL instalado:

```powershell
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe scripts/test_postgres.py
```

El runner crea un cluster nuevo dentro de `tmp/`, ejecuta migraciones y toda la suite PostgreSQL, y detiene el servidor en `finally`. El caso `test_c15_detalle_dos_y_cuatro_renglones_consultas_constantes` guarda su medición en `tmp/postgres-tests-<id>/c15_consultas.txt`. Los SQL de preparación y login no forman parte de esa medición. Se conservan logs en el directorio del cluster detenido; no se necesita ejecutar `seed.py`.

## Alcance y TDD

El repositorio ya declaraba las precargas necesarias: las nuevas regresiones comenzaron verdes. No se presenta un RED retrospectivo ni se cambió producción para satisfacer esta evidencia. La triangulación incluye dos y cuatro renglones, libro dado de baja, distintas vistas paginadas y relaciones opcionales presentes/ausentes. Los resultados de la suite integrada y la trazabilidad final se registran en `openspec/changes/ejercicio-8-lecturas-asincronia/verification.md`.
