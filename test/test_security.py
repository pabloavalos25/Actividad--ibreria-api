import asyncio
import threading
import time

import bcrypt
import pytest

from app.core.security import hash_password


@pytest.mark.parametrize('password,rounds', [('ficticia-uno', 4), ('ficticia-dos', 5)])
def test_hash_es_bcrypt_con_costo_configurado(password, rounds):
    async def scenario():
        hashed = await hash_password(password, rounds=rounds, semaphore=asyncio.Semaphore(1))
        assert bcrypt.checkpw(password.encode(), hashed.encode())
        assert not bcrypt.checkpw(b'otra-password', hashed.encode())
        assert int(hashed.split('$')[2]) == rounds
    asyncio.run(scenario())


@pytest.mark.parametrize('cancellations', [1, 2])
def test_cancelar_no_libera_cupo_hasta_terminar_bcrypt(monkeypatch, cancellations):
    async def scenario():
        started = threading.Event()
        release = threading.Event()
        calls = []

        def blocked_hash(password, salt):
            calls.append(password)
            if password == b'primera':
                started.set()
                if not release.wait(timeout=3):
                    raise RuntimeError('test no liberó trabajador')
            return b'hash-de-prueba'

        monkeypatch.setattr(bcrypt, 'hashpw', blocked_hash)
        semaphore = asyncio.Semaphore(1)
        first = asyncio.create_task(hash_password('primera', rounds=4, semaphore=semaphore))
        assert await asyncio.to_thread(started.wait, 1)
        try:
            for _ in range(cancellations):
                first.cancel()
                await asyncio.sleep(0)
            second = asyncio.create_task(hash_password('segunda', rounds=4, semaphore=semaphore))
            await asyncio.sleep(0.03)
            assert calls == [b'primera']
            assert not first.done()
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert await second == 'hash-de-prueba'
        assert calls == [b'primera', b'segunda']
    asyncio.run(scenario())


@pytest.mark.parametrize('limit', [1, 2])
def test_bcrypt_va_fuera_del_bucle_y_respeta_semaforo(monkeypatch, limit):
    async def scenario():
        loop_thread = threading.get_ident()
        workers = []
        active = peak = 0
        lock = threading.Lock()

        def fake_hash(password, salt):
            nonlocal active, peak
            with lock:
                workers.append(threading.get_ident())
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return b'hash-de-prueba'

        monkeypatch.setattr(bcrypt, 'hashpw', fake_hash)
        semaphore = asyncio.Semaphore(limit)
        results = await asyncio.gather(*(
            hash_password('ficticia', rounds=4, semaphore=semaphore) for _ in range(4)
        ))
        assert results == ['hash-de-prueba'] * 4
        assert all(worker != loop_thread for worker in workers)
        assert peak == limit
    asyncio.run(scenario())
