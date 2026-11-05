import asyncio
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.database import create_engine_and_factory
from app.core.security import hash_password
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.ventas.router import router as ventas_router
from app.modules.usuarios.router import router as usuarios_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
# El echo del motor ya escribe las consultas con su propio handler; sin esto
# cada una saldría dos veces en la consola.
logging.getLogger("sqlalchemy.engine").propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine, session_factory = create_engine_and_factory(
        database_url=settings.database_url,
        echo=settings.echo_sql,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    try:
        app.state.settings = settings
        app.state.bcrypt_semaphore = asyncio.Semaphore(settings.bcrypt_concurrency)
        app.state.dummy_password_hash = await hash_password(
            secrets.token_urlsafe(32), rounds=settings.bcrypt_rounds,
            semaphore=app.state.bcrypt_semaphore,
        )
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="Librería API",
    description="Catálogo, clientes y ventas con FastAPI y PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(usuarios_router)
app.include_router(editoriales_router)
app.include_router(generos_router)
app.include_router(autores_router)
app.include_router(libros_router)
app.include_router(clientes_router)
app.include_router(ventas_router)
