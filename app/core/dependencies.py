from fastapi import HTTPException


async def requerir_usuario_id() -> int:
    """Punto de integración de acceso (ejercicio 4); nunca acepta IDs del cliente.

    Hasta conectar la validación de cookie/usuario/roles, el alta permanece cerrada.
    Las pruebas de integración sustituyen esta dependencia por un usuario real.
    """
    raise HTTPException(401, 'Se requiere una sesión autenticada')
