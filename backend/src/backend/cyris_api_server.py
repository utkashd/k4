from asyncio import wait_for
from contextlib import asynccontextmanager
import datetime
import json
from uuid import UUID
import asyncpg  # type: ignore[import-untyped]
from backend_commons.messages import ClientMessage
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, SecretStr
from connection_management import ConnectionManager
from message_management import ChatPreview, MessageInDb, MessagesManager
from user_management import (
    AdminUser,
    NonAdminUser,
    RegisteredUser,
    RegistrationAttempt,
    UsersManager,
)
from passlib.context import (
    CryptContext,
)  # TODO remove passlib because it's not maintained anymore https://github.com/pyca/bcrypt/issues/684
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
import logging
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")

users_manager = UsersManager()
messages_manager = MessagesManager()
connection_manager = ConnectionManager()
accepted_first = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        """
        we do this because the `finally` clause will *always* be run, even if there's an
        error somewhere during the `yield`
        """
        postgres_connection_pool: asyncpg.Pool = await asyncpg.create_pool(  # type: ignore[annotation-unchecked]
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres",
            min_size=1,
            max_size=5,
        )
        # TODO error handling if connection fails. retry?
        await users_manager.set_connection_pool_and_start(postgres_connection_pool)
        await messages_manager.set_connection_pool_and_start(postgres_connection_pool)
        yield  # everything above the yield is for startup, everything after is for shutdown
    finally:
        await wait_for(
            postgres_connection_pool.close(), 60
        )  # wait 60 seconds for the connections to complete whatever they're doing and close
        # TODO I think I actually want to wait for requests to finish. do that instead


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],  # (protocol, domain, port) defines an origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["*"],
)


SECRET_KEY = "18e8e912cce442d5fe6af43a003dedd7cedd7248efc16ac926f21f8f940398a8"
# TODO generate this when we start for the first time and save it to local machine
# Generated with `openssl rand -hex 32`


class TokenData(BaseModel):
    user_email: EmailStr


pwd_context = CryptContext(schemes=["bcrypt"])
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


async def get_current_active_non_admin_user_ws(websocket: WebSocket) -> NonAdminUser:
    current_user = await get_current_active_user(websocket.cookies.get("authToken"))
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
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

    user = await users_manager.get_active_user_by_email(user_email)

    return user


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> JSONResponse:
    # TODO switch to sessions? https://evertpot.com/jwt-is-a-bad-default/
    JWT_EXPIRE_MINUTES = (
        240  # long only because I plan to remove this in favor of sessions
    )
    user_email = form_data.username
    unhashed_user_password = SecretStr(form_data.password)

    user = await users_manager.get_active_user_by_email(user_email)
    if user.is_user_deactivated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {user.user_email} is a deactivated user.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def is_password_correct(
        unhashed_user_password: SecretStr, hashed_user_password: SecretStr
    ) -> bool:
        return pwd_context.verify(
            unhashed_user_password.get_secret_value(),
            hashed_user_password.get_secret_value(),
        )

    if not is_password_correct(
        unhashed_user_password=unhashed_user_password,
        hashed_user_password=user.hashed_user_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def create_access_token(
        data: dict, minutes_after_which_access_token_expires: int
    ) -> str:
        data_to_encode = data.copy()
        time_access_token_expires = datetime.datetime.now(
            datetime.UTC
        ) + datetime.timedelta(minutes=minutes_after_which_access_token_expires)

        data_to_encode.update({"exp": time_access_token_expires})
        encoded_jwt = jwt.encode(data_to_encode, SECRET_KEY, algorithm="HS256")
        return encoded_jwt

    access_token = create_access_token(
        data={"user_email": user.user_email},
        minutes_after_which_access_token_expires=JWT_EXPIRE_MINUTES,
    )
    response = JSONResponse({"msg": "Login successful"})
    response.set_cookie(
        key="authToken",
        value=access_token,
        httponly=True,
        secure=False,  # TODO change this to true after setting up HTTPS
        samesite="strict",
        max_age=JWT_EXPIRE_MINUTES * 60,
    )
    return response


@app.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"msg": "Logout succcessful"})
    # Overwrite the client's existing `authToken` cookie with an empty/expired one
    response.set_cookie(  # TODO replace with delete cookie
        key="authToken",
        value="",
        httponly=True,
        secure=False,
        expires=0,  # expire the httponly cookie immediately
        max_age=0,
    )
    return response


class FirstAdminDetails(BaseModel):
    desired_user_email: EmailStr
    desired_user_password: SecretStr = Field(max_length=32)


@app.get("/is_setup_required")
async def does_initial_setup_need_to_be_completed() -> bool:
    return not await users_manager.does_at_least_one_active_admin_user_exist()


@app.post("/first_admin")
async def create_first_admin_user(first_admin_details: FirstAdminDetails):
    if await users_manager.does_at_least_one_active_admin_user_exist():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't try to create a user through this endpoint because an admin user has already been created.",
        )
    else:
        hashed_desired_password = SecretStr(
            pwd_context.hash(
                first_admin_details.desired_user_password.get_secret_value()
            )
        )
        return await users_manager.create_user(
            desired_user_email=first_admin_details.desired_user_email,
            hashed_desired_user_password=hashed_desired_password,
            desired_human_name="admin",
            desired_ai_name="U",
            is_user_an_admin=True,
        )


@app.post("/admin")
async def create_admin_user(
    new_user_details: RegistrationAttempt,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> RegisteredUser:
    hashed_desired_password = SecretStr(
        pwd_context.hash(new_user_details.desired_user_password.get_secret_value())
    )
    return await users_manager.create_user(
        desired_user_email=new_user_details.desired_user_email,
        hashed_desired_user_password=hashed_desired_password,
        desired_human_name=new_user_details.desired_human_name,
        desired_ai_name=new_user_details.desired_ai_name,
        is_user_an_admin=True,
    )


@app.post("/user")
async def create_user(
    new_user_details: RegistrationAttempt,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> RegisteredUser:
    hashed_desired_password = SecretStr(
        pwd_context.hash(new_user_details.desired_user_password.get_secret_value())
    )
    return await users_manager.create_user(
        desired_user_email=new_user_details.desired_user_email,
        hashed_desired_user_password=hashed_desired_password,
        desired_human_name=new_user_details.desired_human_name,
        desired_ai_name=new_user_details.desired_ai_name,
    )


@app.delete("/user")
async def deactivate_user(
    user_to_deactivate: RegisteredUser,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
):
    if current_admin_user.user_id == user_to_deactivate.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An admin cannot deactivate their own account. A different admin must do so.",
        )
    await users_manager.deactivate_user(user_to_deactivate)


@app.put("/user")
async def reactivate_user(
    user_to_reactivate: RegisteredUser,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
):
    await users_manager.reactivate_user(user_to_reactivate)


@app.get("/user")
async def get_users(
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> list[RegisteredUser]:
    return await users_manager.get_users()


@app.get("/user/me")
async def get_current_user_info(
    current_user: RegisteredUser = Depends(get_current_active_user),
):
    return current_user


class ChatPreviewsRequestParams(BaseModel):
    after_timestamp: datetime.datetime = datetime.datetime.now()
    num_chats: int = 10


@app.get("/chat")
async def get_chat_by_chat_id(
    chat_id: int,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
):
    if not await messages_manager.does_user_own_this_chat(
        user_id=current_user.user_id, chat_id=chat_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't access a different user's chats.",
        )
    return await messages_manager.get_messages_of_chat(chat_id)


@app.get("/chats")
async def get_chat_previews(
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> list[ChatPreview]:
    return await messages_manager.get_user_chat_previews(current_user.user_id, 20)


class CreateNewChatRequestBody(BaseModel):
    message: str


@app.post("/chat")
async def create_new_chat_with_message(
    msg: CreateNewChatRequestBody,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> list[MessageInDb]:
    chat_in_db = await messages_manager.create_new_chat(
        user_id=current_user.user_id, title=""
    )
    user_message = await messages_manager.save_client_message_to_db(
        chat_id=chat_in_db.chat_id, user_id=current_user.user_id, text=msg.message
    )
    cyris_response_message = await messages_manager.save_cyris_message_to_db(
        chat_id=chat_in_db.chat_id, text="first message, you fancy huh"
    )
    return [user_message, cyris_response_message]


@app.delete("/chat")
async def delete_chat(
    chat_id: int,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
):
    if not messages_manager.does_user_own_this_chat(
        user_id=current_user.user_id, chat_id=chat_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't delete someone else's chat.",
        )
    else:
        await messages_manager.delete_chat(chat_id=chat_id)


class SendMessageRequestBody(BaseModel):
    chat_id: int
    message: str


@app.post("/message")
async def send_message_to_cyris(
    msg: SendMessageRequestBody,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> list[MessageInDb]:
    user_message = await messages_manager.save_client_message_to_db(
        chat_id=msg.chat_id, user_id=current_user.user_id, text=msg.message
    )
    cyris_response_message = await messages_manager.save_cyris_message_to_db(
        chat_id=msg.chat_id, text=f"you sent me: {msg.message} 😎"
    )
    return [user_message, cyris_response_message]


@app.websocket("/chat")
async def websocket_endpoint(
    client_websocket: WebSocket,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user_ws),
) -> None:
    user_id = current_user.user_id
    session_id: UUID | None = None
    try:
        # Accept the connection from the client
        session_id = await connection_manager.connect(client_websocket, user_id)
        while True:
            # Receive the message from the client
            data = json.loads(await client_websocket.receive_text())
            client_message = ClientMessage(**data)
            await connection_manager.save_and_acknowledge_and_reply_to_client_message(
                user_id, client_message
            )
    except WebSocketDisconnect:
        # This means the user disconnected, e.g., closed the browser tab
        if session_id:
            await connection_manager.disconnect(user_id, session_id)


def main() -> None:
    """
    This function needs to be beneath all the endpoint definitions.
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
