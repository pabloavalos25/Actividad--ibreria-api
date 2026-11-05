from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import configure_mappers

from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario
from app.modules.ventas.models import Venta


@pytest.mark.parametrize('linked', [False, True])
def test_usuario_cliente_es_opcional_y_escalar_en_ambos_extremos(linked):
    configure_mappers()
    usuario = Usuario(email='ana@example.test', nombre='Ana', password_hash='hash-de-prueba')
    cliente = Cliente(nombre='Ana', email='ana@example.test')
    if linked:
        cliente.usuario = usuario
        assert cliente.usuario is usuario
        assert usuario.cliente is cliente
        usuario.cliente = None
    assert cliente.usuario is None
    assert usuario.cliente is None


@pytest.mark.parametrize('rol', ['ADMIN', 'VENDEDOR'])
def test_asignacion_distingue_titular_y_otorgante_y_conserva_historial(rol):
    titular = Usuario(email='titular@example.test', nombre='Titular', password_hash='hash')
    admin = Usuario(email='admin@example.test', nombre='Admin', password_hash='hash')
    asignacion = AsignacionRol(usuario=titular, otorgante=admin, rol=rol)
    assert titular.asignaciones == [asignacion]
    assert admin.asignaciones_otorgadas == [asignacion]
    assert admin.asignaciones == []
    assert asignacion.desde.utcoffset() is not None
    asignacion.revocada_en = datetime.now(timezone.utc)
    assert titular.asignaciones == [asignacion]


@pytest.mark.parametrize('cantidad,venta_presente', [(3, False), (-2, True)])
def test_movimiento_navega_libro_usuario_y_venta_opcional(cantidad, venta_presente):
    usuario = Usuario(email='vendedor@example.test', nombre='Vendedor', password_hash='hash')
    libro = Libro(isbn='ISBN-TEST', titulo='Libro', precio=Decimal('10.25'),
                  stock=3, editorial=Editorial(nombre='Editorial'))
    cliente = Cliente(nombre='Cliente', email='cliente@example.test')
    venta = Venta(cliente=cliente, total=Decimal('20.50')) if venta_presente else None
    movimiento = MovimientoStock(libro=libro, usuario=usuario, venta=venta,
                                 cantidad=cantidad, motivo='Prueba')
    assert libro.movimientos == [movimiento]
    assert usuario.movimientos_stock == [movimiento]
    assert movimiento.venta is venta
    if venta is not None:
        assert venta.movimientos_stock == [movimiento]
    assert movimiento.cuando.utcoffset() is not None
    assert libro.precio == Decimal('10.25')
    assert libro.borrado_en is None


@pytest.mark.parametrize('exito', [False, True])
def test_intentos_y_eventos_no_requieren_usuario(exito):
    intento = IntentoAcceso(email='inexistente@example.test', ip='127.0.0.1', exito=exito)
    evento = EventoSeguridad(actor='SISTEMA', accion='Carga de los datos iniciales')
    assert intento.email == 'inexistente@example.test'
    assert intento.exito is exito
    assert evento.actor == 'SISTEMA'
    assert intento.cuando.utcoffset() is not None
    assert evento.cuando.utcoffset() is not None
