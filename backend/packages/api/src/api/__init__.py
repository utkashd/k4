from ._dependencies import lifespan
from .auth import auth_router
from .chats import chats_router
from .extensions import extensions_router
from .providers import providers_router
from .setup import setup_router
from .users import users_router

__all__ = [
    "auth_router",
    "chats_router",
    "extensions_router",
    "setup_router",
    "users_router",
    "providers_router",
    "lifespan",
]
