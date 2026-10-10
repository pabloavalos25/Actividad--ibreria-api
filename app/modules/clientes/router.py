from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.ventas import service as ventas_service
from app.modules.ventas.schemas import VentaRead

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("/", response_model=ClienteRead, status_code=201)
async def crear_cliente(
    datos: ClienteCreate,
    session: AsyncSession = Depends(get_session),
) -> ClienteRead:
    cliente = await service.crear_cliente(session, datos)
    return service.a_read(cliente)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def obtener_cliente(
    cliente_id: int,
    session: AsyncSession = Depends(get_session),
) -> ClienteRead:
    cliente = await service.obtener_cliente(session, cliente_id)
    return service.a_read(cliente)


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def actualizar_cliente(
    cliente_id: int,
    datos: ClienteUpdate,
    session: AsyncSession = Depends(get_session),
) -> ClienteRead:
    cliente = await service.actualizar_cliente(session, cliente_id, datos)
    return service.a_read(cliente)


@router.post("/{cliente_id}/perfil", response_model=PerfilRead, status_code=201)
async def crear_perfil(
    cliente_id: int,
    datos: PerfilCreate,
    session: AsyncSession = Depends(get_session),
) -> PerfilRead:
    perfil = await service.crear_perfil(session, cliente_id, datos)
    return service.perfil_a_read(perfil)


@router.get("/{cliente_id}/ventas", response_model=list[VentaRead])
async def listar_ventas_de_cliente(
    cliente_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[VentaRead]:
    ventas = await ventas_service.listar_ventas_de_cliente(session, cliente_id)
    return [ventas_service.a_read(venta) for venta in ventas]
