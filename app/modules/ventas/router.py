from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaRead

router = APIRouter(prefix="/ventas", tags=["ventas"])


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
