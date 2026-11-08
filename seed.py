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
from app.core.security import hash_password
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario

PASSWORD_INICIAL = "secreto123"

USUARIOS_INICIALES = (
    ("Administrador", "admin@example.com", "ADMIN", False),
    ("Administrador Auxiliar", "admin2@example.com", "ADMIN", False),
    ("Vendedor", "vendedor@example.com", "VENDEDOR", False),
    ("Ana Paz", "ana@example.com", "CLIENTE", False),
    ("Vendedor Nuevo", "nuevo@example.com", "VENDEDOR", True),
)

VACIAR_TABLAS = text(
    "TRUNCATE movimiento_stock, renglon_venta, venta, perfil_cliente, "
    "cliente, libro_autor, libro, autor, genero, editorial, "
    "asignacion_rol, usuario, intento_acceso, evento_seguridad "
    "RESTART IDENTITY CASCADE"
)


async def agregar(session: AsyncSession, *objetos) -> None:
    # Un flush por objeto: los ids se asignan en el orden en que se listan.
    for objeto in objetos:
        session.add(objeto)
        await session.flush()


async def cargar(session: AsyncSession, *, rounds: int = 4) -> None:
    # Regla dura 6: calcular hashes bcrypt fuera del bucle de eventos y antes de abrir transacción.
    semaphore = asyncio.Semaphore(4)
    hashes = [
        await hash_password(PASSWORD_INICIAL, rounds=rounds, semaphore=semaphore)
        for _ in USUARIOS_INICIALES
    ]

    await session.execute(VACIAR_TABLAS)

    await agregar(
        session,
        *(
            Usuario(
                nombre=nombre,
                email=email,
                password_hash=pwd_hash,
                activo=True,
                debe_cambiar_password=debe_cambiar,
            )
            for (nombre, email, _rol, debe_cambiar), pwd_hash in zip(
                USUARIOS_INICIALES, hashes, strict=True
            )
        ),
    )
    await agregar(
        session,
        *(
            AsignacionRol(
                usuario_id=idx,
                rol=rol,
                otorgada_por=1 if rol in ("ADMIN", "VENDEDOR") else None,
            )
            for idx, (_nombre, _email, rol, _debe_cambiar) in enumerate(
                USUARIOS_INICIALES, start=1
            )
        ),
    )

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
        Autor(nombre="Alejandra Pizarnik", nacionalidad="Argentina"),
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
            isbn="978-950-00-0002-8",
            titulo="Antología de la literatura fantástica",
            precio=Decimal("30000.00"),
            stock=5,
            editorial_id=1,
            genero_id=3,
            autorias=[
                LibroAutor(autor_id=5, rol="coautor", orden=1),
                LibroAutor(autor_id=4, rol="coautor", orden=2),
                LibroAutor(autor_id=3, rol="coautor", orden=3),
            ],
        ),
        Libro(
            isbn="978-950-00-0003-3",
            titulo="Ficciones",
            precio=Decimal("22000.00"),
            stock=8,
            editorial_id=1,
            genero_id=3,
            autorias=[LibroAutor(autor_id=5, rol="autor", orden=1)],
        ),
        Libro(
            isbn="978-950-00-0004-4",
            titulo="Respiración artificial",
            precio=Decimal("27000.00"),
            stock=3,
            editorial_id=3,
            genero_id=2,
            autorias=[LibroAutor(autor_id=2, rol="autor", orden=1)],
        ),
        Libro(
            isbn="978-950-00-0005-5",
            titulo="Bestiario",
            precio=Decimal("19500.00"),
            stock=1,
            editorial_id=2,
            genero_id=3,
            autorias=[LibroAutor(autor_id=1, rol="autor", orden=1)],
        ),
    )
    await agregar(
        session,
        Cliente(nombre="Lucía Fernández", email="lucia@example.com"),
        Cliente(nombre="Tomás Ríos", email="tomas@example.com"),
        Cliente(nombre="Ana Paz", email="ana@example.com", usuario_id=4),
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
            total=Decimal("69000.00"),
            renglones=[
                RenglonVenta(
                    libro_id=1,
                    cantidad=1,
                    precio_unitario=Decimal("25000.00"),
                ),
                RenglonVenta(
                    libro_id=3,
                    cantidad=2,
                    precio_unitario=Decimal("22000.00"),
                ),
            ],
        ),
    )
    await agregar(
        session,
        MovimientoStock(
            libro_id=1,
            usuario_id=1,
            cantidad=11,
            motivo="Stock inicial",
        ),
        MovimientoStock(
            libro_id=2,
            usuario_id=1,
            cantidad=5,
            motivo="Stock inicial",
        ),
        MovimientoStock(
            libro_id=3,
            usuario_id=1,
            cantidad=10,
            motivo="Stock inicial",
        ),
        MovimientoStock(
            libro_id=4,
            usuario_id=1,
            cantidad=3,
            motivo="Stock inicial",
        ),
        MovimientoStock(
            libro_id=5,
            usuario_id=1,
            cantidad=1,
            motivo="Stock inicial",
        ),
        MovimientoStock(
            libro_id=1,
            venta_id=1,
            usuario_id=3,
            cantidad=-1,
            motivo="Venta 1",
        ),
        MovimientoStock(
            libro_id=3,
            venta_id=1,
            usuario_id=3,
            cantidad=-2,
            motivo="Venta 1",
        ),
    )
    await agregar(session, EventoSeguridad(actor='SISTEMA', accion='Carga de los datos iniciales'))
    await session.commit()


async def main() -> None:
    settings = get_settings()
    engine, session_factory = create_engine_and_factory(
        database_url=settings.database_url,
        echo=settings.echo_sql,
    )
    try:
        async with session_factory() as session:
            await cargar(session, rounds=settings.bcrypt_rounds)
    finally:
        await engine.dispose()
    print(
        "Estado inicial cargado: 5 usuarios con roles, 3 editoriales, "
        "3 géneros, 6 autores, 5 libros, 3 clientes (1 con perfil), "
        "1 venta, 7 movimientos de stock y 1 evento SISTEMA."
    )


if __name__ == "__main__":
    asyncio.run(main())
