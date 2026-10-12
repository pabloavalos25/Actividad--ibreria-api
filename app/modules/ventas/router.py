import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaRead

logger = logging.getLogger("libreria.ventas")

router = APIRouter(prefix="/ventas", tags=["ventas"])


async def enviar_comprobante(
    venta_id: int,
    cliente_email: str,
    total: str,
) -> None:
    await asyncio.sleep(0.5)
    logger.info(
        "Comprobante de venta #%s enviado a %s (total %s)",
        venta_id,
        cliente_email,
        total,
    )


@router.post("/", response_model=VentaRead, status_code=201)
async def crear_venta(
    datos: VentaCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> VentaRead:
    venta = await service.crear_venta(session, datos)
    respuesta = service.a_read(venta)
    background_tasks.add_task(
        enviar_comprobante,
        venta_id=respuesta.id,
        cliente_email=respuesta.cliente.email,
        total=str(respuesta.total),
    )
    return respuesta


@router.get("/", response_model=list[VentaRead])
async def listar_ventas(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[VentaRead]:
    ventas = await service.listar_ventas(session, limit, offset)
    return [service.a_read(venta) for venta in ventas]


@router.get("/{venta_id}", response_model=VentaRead)
async def obtener_venta(
    venta_id: int,
    session: AsyncSession = Depends(get_session),
) -> VentaRead:
    venta = await service.obtener_venta(session, venta_id)
    return service.a_read(venta)
