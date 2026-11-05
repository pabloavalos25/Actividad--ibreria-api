"""Bcrypt fuera del bucle de eventos y JWT firmado para cookies de acceso."""

import asyncio

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone


async def hash_password(
    password: str, *, rounds: int, semaphore: asyncio.Semaphore,
) -> str:
    def calculate() -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=rounds)).decode('ascii')

    async with semaphore:
        worker = asyncio.create_task(asyncio.to_thread(calculate))
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            # Cancelar la coroutine no detiene el hilo: conservar su cupo hasta
            # que termine, incluso si llega otra cancelación durante la espera.
            while not worker.done():
                try:
                    await asyncio.shield(worker)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not worker.cancelled():
                worker.exception()
            raise


async def verify_password(password: str, hashed: str, *, semaphore: asyncio.Semaphore) -> bool:
    async with semaphore:
        worker = asyncio.create_task(asyncio.to_thread(
            bcrypt.checkpw, password.encode('utf-8'), hashed.encode('ascii'),
        ))
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            while not worker.done():
                try:
                    await asyncio.shield(worker)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not worker.cancelled():
                worker.exception()
            raise


def create_token(usuario_id: int, roles: list[str], *, secret: str, ttl: int) -> str:
    return jwt.encode(dict(sub=str(usuario_id), roles=roles,
                           exp=datetime.now(timezone.utc) + timedelta(seconds=ttl)), secret, algorithm='HS256')


def decode_token(token: str, *, secret: str) -> dict:
    claims = jwt.decode(token, secret, algorithms=['HS256'], options={'require': ['sub', 'exp']})
    if len(claims['sub']) > 10 or not claims['sub'].isascii() or not claims['sub'].isdigit() or not 0 < int(claims['sub']) <= 2147483647:
        raise jwt.InvalidTokenError('Sujeto inválido')
    if not isinstance(claims.get('roles'), list) or not all(isinstance(r, str) for r in claims['roles']):
        raise jwt.InvalidTokenError('Roles inválidos')
    return claims
