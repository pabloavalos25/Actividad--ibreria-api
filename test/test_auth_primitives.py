import asyncio
import threading
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import verify_password, create_token, decode_token
from app.modules.usuarios.schemas import Registro, Login, CambiarPassword


@pytest.mark.parametrize('schema,values', [
    (Registro, dict(nombre='Ana',email='ana@example.com',password='á'*37)),
    (Login, dict(email='ana@example.com',password='á'*37)),
    (CambiarPassword, dict(password_actual='á'*37,password_nueva='abcdefgh')),
    (CambiarPassword, dict(password_actual='abcdefgh',password_nueva='á'*37)),
    (Registro, dict(nombre='Ana',email='ana@example.com',password='abcdefgh',roles=['ADMIN'])),
    (Registro, dict(nombre='Ana',email='ana@example.com',password='corta')),
])
def test_password_y_campos_invalidos(schema,values):
    with pytest.raises(ValidationError): schema(**values)


@pytest.mark.parametrize('password', ['abcdefgh','á'*36])
def test_limite_valido(password):
    assert Registro(nombre='Ana',email='Ana@EXAMPLE.COM',password=password).password == password
    assert Login(email='ana@example.com',password=password).password == password


@pytest.mark.parametrize('password', ['abcdefgh','otra-clave'])
def test_verify_bcrypt_fuera_eventloop(password,monkeypatch):
    async def scenario():
        current=threading.get_ident(); workers=[]
        original=bcrypt.checkpw
        def check(value,hashed):
            workers.append(threading.get_ident()); return original(value,hashed)
        monkeypatch.setattr(bcrypt,'checkpw',check)
        hashed=bcrypt.hashpw(b'abcdefgh',bcrypt.gensalt(rounds=4)).decode()
        assert await verify_password(password,hashed,semaphore=asyncio.Semaphore(1)) == (password=='abcdefgh')
        assert workers and all(t!=current for t in workers)
    asyncio.run(scenario())


@pytest.mark.parametrize('ttl',[60,1800])
def test_token_claims_y_firma(ttl):
    secret='test-signature-that-is-at-least-32-bytes'
    token=create_token(7,['ADMIN'],secret=secret,ttl=ttl)
    claims=decode_token(token,secret=secret)
    assert claims['sub']=='7' and claims['roles']==['ADMIN']
    assert abs(claims['exp']-datetime.now(timezone.utc).timestamp()-ttl)<2
    with pytest.raises(jwt.InvalidTokenError): decode_token(token,secret='otra-clave-de-firma-de-32-bytes-minimo')


@pytest.mark.parametrize('claims',[{'sub':'1'}, {'sub':'1','exp':datetime.now(timezone.utc)-timedelta(seconds=1)}])
def test_token_incompleto_o_vencido(claims):
    secret='test-signature-that-is-at-least-32-bytes'
    with pytest.raises(jwt.InvalidTokenError): decode_token(jwt.encode(claims,secret,algorithm='HS256'),secret=secret)


def test_defaults_auth_settings():
    settings=Settings(_env_file=None,postgres_user='u',postgres_password='p',postgres_db='d',postgres_host='h',jwt_secret='s')
    assert settings.jwt_ttl_seconds==1800 and settings.cookie_secure is False


@pytest.mark.parametrize('subject',['1'*5000,123,'-1','2147483648'])
def test_sujeto_invalido_es_error_token(subject):
    secret='test-signature-that-is-at-least-32-bytes'
    token=jwt.encode(dict(sub=subject,roles=[],exp=datetime.now(timezone.utc)+timedelta(seconds=60)),secret,algorithm='HS256')
    with pytest.raises(jwt.InvalidTokenError): decode_token(token,secret=secret)
