import uuid
from asyncio import wait_for
from contextlib import asynccontextmanager

import asyncpg
import bcrypt
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from utils.environment import is_running_in_docker_container

from k4 import K4

from .extension_management import ExtensionsManager
from .message_management import MessagesManager
from .session_management import SessionsManager
from .user_management import AdminUser, NonAdminUser, UsersManager

users_manager = UsersManager()
sessions_manager = SessionsManager()
messages_manager = MessagesManager()
extensions_manager = ExtensionsManager()
k4 = K4()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    async def create_postgres_connection_pool() -> "asyncpg.Pool[asyncpg.Record]":
        postgres_host = (
            "k4-postgres" if is_running_in_docker_container() else "localhost"
        )
        postgres_connection_pool_or_none = await asyncpg.create_pool(
            host=postgres_host,
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres",
            min_size=1,
            max_size=15,
        )
        assert postgres_connection_pool_or_none is not None
        return postgres_connection_pool_or_none

    postgres_connection_pool = None
    try:
        # we do this because the `finally` clause will *always* be run, even if there's an
        # error somewhere during the `yield`
        postgres_connection_pool = await create_postgres_connection_pool()
        await users_manager.set_connection_pool_and_start(postgres_connection_pool)
        await messages_manager.set_connection_pool_and_start(postgres_connection_pool)
        await extensions_manager.set_connection_pool_and_start(postgres_connection_pool)
        await sessions_manager.set_connection_pool_and_start(postgres_connection_pool)
        await k4.setup_llm_providers_from_disk()
        yield  # everything above the yield is for startup, everything after is for shutdown
    finally:
        if postgres_connection_pool:
            await wait_for(
                postgres_connection_pool.close(), 60
            )  # wait 60 seconds for the connections to complete whatever they're doing and close
            # TODO I think I actually want to wait for requests to finish. do that instead


class TokenData(BaseModel):
    user_email: EmailStr


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode(encoding="utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        password=plain_password.encode("utf-8"),
        hashed_password=hashed_password.encode("utf-8"),
    )


async def get_current_active_admin_user(request: Request) -> AdminUser:
    current_user = await get_current_active_user(request)
    if not isinstance(current_user, AdminUser):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {current_user.user_email} is not an administrator.",
        )
    return current_user


async def get_current_active_non_admin_user(request: Request) -> NonAdminUser:
    current_user = await get_current_active_user(request)
    if not isinstance(current_user, NonAdminUser):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {current_user.user_email} is an administrator.",
        )
    return current_user


async def get_current_active_user(request: Request) -> AdminUser | NonAdminUser:
    session_id = request.cookies.get("sessionId")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: sessionId not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session = await sessions_manager.get_unexpired_session(
        session_id=uuid.UUID(session_id)
    )

    return await users_manager.get_user_by_user_id(user_id=session.user_id)
