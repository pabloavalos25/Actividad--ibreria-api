# Roadmap — Librería (FastAPI + PostgreSQL)

TP Programación III, capítulos 1 a 4. Fuente de verdad del avance.
Persistencia entre sesiones: engram (`--project libreria-api`), hitos al cerrar fases 0, 3, 5 y 8.

| # | Fase | Estado | Verificación |
|---|------|--------|--------------|
| 0 | Repo base: git, requirements, .env/.env.example, venv, ROADMAP | [x] | `pip install` OK |
| 1 | Core y ciclo de vida: config, database, main (lifespan), health live/ready | [x] | server levanta, 200 en ambos health |
| 2 | Modelos: 7 módulos, UNIQUE/CHECK/FK+índice, back_populates en ambos extremos, Decimal | [x] | importa `app.main` sin errores |
| 3 | Migraciones: rev1 (todo menos genero), rev2 (genero + libro.genero_id) | [x] | upgrade → downgrade -1 → upgrade |
| 4 | Contratos y CRUD: schemas, service/router, paginación RN-10, exclude_unset, 409 propios, sin PATCH ventas | [x] | códigos HTTP correctos |
| 5 | Altas con relaciones: POST /libros, POST /ventas (renglones anidados) | [x] | RN-04…RN-07 |
| 6 | Lecturas sin N+1: joinedload/selectinload | [x] | nº fijo de consultas en consola |
| 7 | Asincronía: async def + BackgroundTasks (asyncio.sleep(0.5)) | [ ] | log del comprobante |
| 8 | Tests y entrega: seed.py, test/*.http C-01…C-08, README, evidencia C-07 | [ ] | los 8 casos pasan |

Orden crítico lineal: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.

## Reglas duras del TP
- Nombres de tablas/columnas exactos (los usan los tests); no renombrar ni quitar.
- Dinero con `Decimal` (NUMERIC), nunca `float`.
- Sin `create_all`: esquema solo con Alembic (plantilla asíncronica).
- Sin credenciales reales en el repo; `.env` no se sube.
- Ningún error expone texto de la base (RN-12).
- Handlers `async def`, sin llamadas bloqueantes; lazy loading prohibido.

## Pendiente / notas
- BD local PostgreSQL 17.10 en 127.0.0.1:5432 (consigna pide ≥16); base `libreria` creada; credenciales en `.env` (no se sube).
- `ECHO_SQL=true` en el entorno activa `echo=True` del motor (diagnóstico de consultas).
- fastapi instalado 0.143.0 (el `[standard]` no existe en 0.111, por eso `>=0.111`).
