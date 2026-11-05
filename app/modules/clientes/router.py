from app.core.dependencies import requiere_admin, requiere_personal, get_usuario_actual
from typing import Annotated
from fastapi import Path
from app.core.paginacion import Pagina
from fastapi import APIRouter, Depends, Query

from app.modules.clientes.unit_of_work import get_uow
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.ventas import service as ventas_service
from app.modules.ventas.unit_of_work import get_uow as get_ventas_uow
from app.modules.ventas.schemas import VentaRead

public_router = APIRouter(prefix="/clientes", tags=["clientes"])
protected_router = APIRouter(prefix="/clientes", tags=["clientes"])



@protected_router.post("/", response_model=ClienteRead, status_code=201, dependencies=[Depends(requiere_personal)])
async def crear_cliente(
    datos: ClienteCreate,
    uow = Depends(get_uow),
) -> ClienteRead:
    cliente = await service.crear_cliente(uow, datos)
    return service.a_read(cliente)


@protected_router.get("/{cliente_id}", response_model=ClienteRead, dependencies=[Depends(requiere_personal)])
async def obtener_cliente(
    cliente_id: Annotated[int, Path(gt=0, le=2147483647)],
    uow = Depends(get_uow),
) -> ClienteRead:
    cliente = await service.obtener_cliente(uow, cliente_id)
    return service.a_read(cliente)


@protected_router.patch("/{cliente_id}", response_model=ClienteRead, dependencies=[Depends(requiere_personal)])
async def actualizar_cliente(
    cliente_id: Annotated[int, Path(gt=0, le=2147483647)],
    datos: ClienteUpdate,
    uow = Depends(get_uow),
) -> ClienteRead:
    cliente = await service.actualizar_cliente(uow, cliente_id, datos)
    return service.a_read(cliente)


@protected_router.post("/{cliente_id}/perfil", response_model=PerfilRead, status_code=201, dependencies=[Depends(requiere_personal)])
async def crear_perfil(
    cliente_id: Annotated[int, Path(gt=0, le=2147483647)],
    datos: PerfilCreate,
    uow = Depends(get_uow),
) -> PerfilRead:
    perfil = await service.crear_perfil(uow, cliente_id, datos)
    return service.perfil_a_read(perfil)


@protected_router.get("/{cliente_id}/ventas", response_model=Pagina[VentaRead], dependencies=[Depends(requiere_personal)])
async def listar_ventas_de_cliente(
    cliente_id: Annotated[int, Path(gt=0, le=2147483647)],
    size: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    uow = Depends(get_ventas_uow),
) -> dict:
    ventas = await ventas_service.listar_ventas_de_cliente(
        uow, cliente_id, page, size
    )
    ventas["items"] = [ventas_service.a_read(venta) for venta in ventas["items"]]
    return ventas


router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
