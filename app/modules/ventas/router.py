from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.modules.ventas.unit_of_work import get_uow
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaRead

logger = logging.getLogger("libreria.ventas")

public_router = APIRouter(prefix="/ventas", tags=["ventas"])
protected_router = APIRouter(prefix="/ventas", tags=["ventas"])



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


@protected_router.post("/", response_model=VentaRead, status_code=201, dependencies=[Depends(requiere_personal)])
async def crear_venta(
    datos: VentaCreate,
    background_tasks: BackgroundTasks,
    usuario=Depends(requiere_personal),
    uow = Depends(get_uow),
) -> VentaRead:
    venta = await service.crear_venta(uow, datos, usuario_id=usuario.id)
    respuesta = service.a_read(venta)
    background_tasks.add_task(
        enviar_comprobante,
        venta_id=respuesta.id,
        cliente_email=respuesta.cliente.email,
        total=str(respuesta.total),
    )
    return respuesta


@protected_router.get("/", response_model=Pagina[VentaRead], dependencies=[Depends(requiere_personal)])
async def listar_ventas(
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    uow = Depends(get_uow),
) -> dict:
    ventas = await service.listar_ventas(uow, page, size)
    ventas["items"] = [service.a_read(venta) for venta in ventas["items"]]
    return ventas


@protected_router.get("/{venta_id}", response_model=VentaRead, dependencies=[Depends(get_usuario_actual)])
async def obtener_venta(
    venta_id: Annotated[int, Path(gt=0, le=2147483647)],
    usuario=Depends(get_usuario_actual),
    uow = Depends(get_uow),
) -> VentaRead:
    venta = await service.obtener_venta(uow, venta_id, usuario.id)
    return service.a_read(venta)


mis_ventas_router = APIRouter()


@mis_ventas_router.get('/mis-ventas', response_model=Pagina[VentaRead])
async def mis_ventas(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                     usuario=Depends(get_usuario_actual), uow=Depends(get_uow)):
    pagina = await service.mis_ventas(uow, usuario.id, page, size)
    pagina['items'] = [service.a_read(venta) for venta in pagina['items']]
    return pagina


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
router.include_router(mis_ventas_router)
