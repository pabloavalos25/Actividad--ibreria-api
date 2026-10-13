"""Deja la base en un estado inicial conocido para los casos de prueba.

Uso:  python seed.py

Vacía las tablas del dominio, reinicia los identificadores y carga siempre
los mismos datos, de modo que los ids que usan los archivos de test/ sean
estables. Requiere el esquema ya creado con `alembic upgrade head`.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import create_engine_and_factory
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta

VACIAR_TABLAS = text(
    "TRUNCATE renglon_venta, venta, perfil_cliente, cliente, "
    "libro_autor, libro, autor, genero, editorial "
    "RESTART IDENTITY CASCADE"
)


async def agregar(session: AsyncSession, *objetos) -> None:
    # Un flush por objeto: los ids se asignan en el orden en que se listan.
    for objeto in objetos:
        session.add(objeto)
        await session.flush()


async def cargar(session: AsyncSession) -> None:
    await session.execute(VACIAR_TABLAS)

    await agregar(
        session,
        Editorial(nombre="Emecé", pais="Argentina"),
        Editorial(nombre="Sudamericana", pais="Argentina"),
        Editorial(nombre="Anagrama", pais="España"),
    )
    await agregar(
        session,
        Genero(nombre="Policial"),
        Genero(nombre="Novela"),
        Genero(nombre="Cuento"),
    )
    await agregar(
        session,
        Autor(nombre="Julio Cortázar", nacionalidad="Argentina"),
        Autor(nombre="Ricardo Piglia", nacionalidad="Argentina"),
        Autor(nombre="Silvina Ocampo", nacionalidad="Argentina"),
        Autor(nombre="Adolfo Bioy Casares", nacionalidad="Argentina"),
        Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina"),
    )
    await agregar(
        session,
        Libro(
            isbn="978-950-00-0001-1",
            titulo="Rayuela",
            precio=Decimal("25000.00"),
            stock=10,
            editorial_id=2,
            genero_id=2,
            autorias=[LibroAutor(autor_id=1, rol="autor", orden=1)],
        ),
        Libro(
            isbn="978-950-00-0002-2",
            titulo="Ficciones",
            precio=Decimal("18000.00"),
            stock=8,
            editorial_id=1,
            genero_id=3,
            autorias=[LibroAutor(autor_id=5, rol="autor", orden=1)],
        ),
        Libro(
            isbn="978-950-00-0003-3",
            titulo="La invención de Morel",
            precio=Decimal("16500.00"),
            stock=6,
            editorial_id=1,
            genero_id=None,
            autorias=[LibroAutor(autor_id=4, rol="autor", orden=1)],
        ),
        Libro(
            isbn="978-950-00-0004-4",
            titulo="Respiración artificial",
            precio=Decimal("27000.00"),
            stock=5,
            editorial_id=3,
            genero_id=2,
            autorias=[LibroAutor(autor_id=2, rol="autor", orden=1)],
        ),
        Libro(
            isbn="978-950-00-0005-5",
            titulo="Seis problemas para don Isidro Parodi",
            precio=Decimal("19500.00"),
            stock=4,
            editorial_id=2,
            genero_id=1,
            autorias=[
                LibroAutor(autor_id=5, rol="coautor", orden=1),
                LibroAutor(autor_id=4, rol="coautor", orden=2),
            ],
        ),
    )
    await agregar(
        session,
        Cliente(nombre="Ana Gómez", email="ana@example.com"),
        Cliente(nombre="Tomás Ríos", email="tomas@example.com"),
        Cliente(nombre="Lucía Paz", email="lucia@example.com"),
    )
    await agregar(
        session,
        PerfilCliente(
            cliente_id=1,
            telefono="+54 11 5555-0101",
            direccion="Av. Corrientes 1234, CABA",
        ),
    )
    await agregar(
        session,
        Venta(
            cliente_id=1,
            total=Decimal("18000.00"),
            renglones=[
                RenglonVenta(
                    libro_id=2,
                    cantidad=1,
                    precio_unitario=Decimal("18000.00"),
                )
            ],
        ),
        Venta(
            cliente_id=3,
            total=Decimal("64000.00"),
            renglones=[
                RenglonVenta(
                    libro_id=1,
                    cantidad=1,
                    precio_unitario=Decimal("25000.00"),
                ),
                RenglonVenta(
                    libro_id=5,
                    cantidad=2,
                    precio_unitario=Decimal("19500.00"),
                ),
            ],
        ),
    )
    await session.commit()


async def main() -> None:
    settings = get_settings()
    engine, session_factory = create_engine_and_factory(
        database_url=settings.database_url,
        echo=settings.echo_sql,
    )
    try:
        async with session_factory() as session:
            await cargar(session)
    finally:
        await engine.dispose()
    print(
        "Estado inicial cargado: 3 editoriales, 3 géneros, 5 autores, "
        "5 libros, 3 clientes (1 con perfil) y 2 ventas."
    )


if __name__ == "__main__":
    asyncio.run(main())
