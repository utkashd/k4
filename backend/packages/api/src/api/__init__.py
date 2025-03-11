from .chats import chats_router
from .dependencies import lifespan
from .extensions import extensions_router
from .setup import setup_router
from .users import users_router

__all__ = [
    "chats_router",
    "extensions_router",
    "setup_router",
    "users_router",
    "lifespan",
]
