from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaRead
from app.modules.usuarios.repository import UsuarioRepository
from app.modules.usuarios.service import ahora_utc
from app.modules.clientes.models import Cliente
from sqlalchemy import select
from app.core.paginacion import paginar
from app.modules.ventas.models import Venta
from fastapi import HTTPException

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


@protected_router.get("/", response_model=Pagina[VentaRead], dependencies=[Depends(requiere_personal)])
async def listar_ventas(
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session),
) -> dict:
    ventas = await service.listar_ventas(session, page, size)
    ventas["items"] = [service.a_read(venta) for venta in ventas["items"]]
    return ventas


@protected_router.get("/{venta_id}", response_model=VentaRead, dependencies=[Depends(get_usuario_actual)])
async def obtener_venta(
    venta_id: Annotated[int, Path(gt=0, le=2147483647)],
    usuario=Depends(get_usuario_actual),
    session: AsyncSession = Depends(get_session),
) -> VentaRead:
    venta = await service.obtener_venta(session, venta_id)
    roles = await UsuarioRepository(session).roles_vigentes(usuario.id, ahora_utc())
    if not set(roles).intersection(('ADMIN', 'VENDEDOR')) and venta.cliente.usuario_id != usuario.id:
        raise HTTPException(403, 'No tiene permiso para consultar esta venta')
    return service.a_read(venta)


mis_ventas_router = APIRouter()


@mis_ventas_router.get('/mis-ventas', response_model=Pagina[VentaRead])
async def mis_ventas(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                     usuario=Depends(get_usuario_actual), session=Depends(get_session)):
    pagina = await paginar(session, select(Venta).join(Cliente).where(Cliente.usuario_id == usuario.id)
                           .options(*service.opciones_venta).order_by(Venta.id), page, size)
    pagina['items'] = [service.a_read(venta) for venta in pagina['items']]
    return pagina


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
router.include_router(mis_ventas_router)
