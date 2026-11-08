"""Punto de entrada en la raíz del proyecto compatible con la estructura de la consigna.

Reexporta la instancia ASGI ``app`` y el administrador de ciclo de vida ``lifespan``
definidos en ``app.main``, junto con el ayudante ``create_app()``, para que tanto
``uvicorn app.main:app`` como ``uvicorn main:app`` ejecuten la misma aplicación FastAPI.
"""

from fastapi import FastAPI

from app.main import app, lifespan


def create_app() -> FastAPI:
    """Devuelve la instancia configurada de la aplicación FastAPI."""
    return app


__all__ = ["app", "lifespan", "create_app"]
