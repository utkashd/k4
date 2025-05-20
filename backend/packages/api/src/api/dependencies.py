import os
from asyncio import wait_for
from contextlib import asynccontextmanager

import asyncpg
import bcrypt
from fastapi import Cookie, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from utils.environment import is_running_in_docker_container

from k4 import K4

from .extension_management import ExtensionsManager
from .message_management import MessagesManager
from .user_management import AdminUser, NonAdminUser, UsersManager

SECRET_KEY = os.environ["K4_BACKEND_SECRET_KEY"]

users_manager = UsersManager()
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

    try:
        # we do this because the `finally` clause will *always* be run, even if there's an
        # error somewhere during the `yield`
        postgres_connection_pool = await create_postgres_connection_pool()
        await users_manager.set_connection_pool_and_start(postgres_connection_pool)
        await messages_manager.set_connection_pool_and_start(postgres_connection_pool)
        await extensions_manager.set_connection_pool_and_start(postgres_connection_pool)
        await k4.setup_llm_providers_from_disk()
        yield  # everything above the yield is for startup, everything after is for shutdown
    finally:
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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_active_admin_user(request: Request) -> AdminUser:
    current_user = await get_current_active_user(request.cookies.get("authToken"))
    if not isinstance(current_user, AdminUser):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {current_user.user_email} is not an administrator.",
        )
    return current_user


async def get_current_active_non_admin_user(request: Request) -> NonAdminUser:
    current_user = await get_current_active_user(request.cookies.get("authToken"))
    if not isinstance(current_user, NonAdminUser):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {current_user.user_email} is an administrator.",
        )
    return current_user


async def get_current_active_user(
    authToken: str | None = Cookie(default=None),
) -> AdminUser | NonAdminUser:
    # token = request.cookies.get("authToken")
    token = authToken
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: authToken not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token=token, key=SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_email = payload.get("user_email")
    if not user_email or not isinstance(user_email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unexpected issue encountered when attempting to validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await users_manager.get_active_user_by_email(
        user_email
    )  # TODO get by user id which will be much faster

    return user
