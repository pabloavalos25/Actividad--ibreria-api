"""Primitiva de bcrypt compartida; los endpoints de acceso se agregan después."""

import asyncio

import bcrypt


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
