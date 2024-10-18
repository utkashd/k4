from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI, HTTPException  # , Depends, HTTPException, status

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, SecretStr
from user_management import (
    # ChatPreview,
    # RegisteredUser,
    RegisteredUser,
    RegistrationAttempt,
    UsersManagerAsync,
)
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer  # , OAuth2PasswordRequestForm

# from backend_commons.messages import (
#     ClientMessage,
#     Message,
# )
# from langchain_core.messages import HumanMessage, AIMessage
# from langchain_community.chat_message_histories.in_memory import ChatMessageHistory


users_manager: UsersManagerAsync | None = None


pwd_context = CryptContext(schemes=["bcrypt"])
oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# async def authenticate_user(
#     user_email: EmailStr, unhashed_user_password: SecretStr
# ) -> RegisteredUser | None:
#     assert isinstance(users_manager, UsersManagerAsync)
#     user = await users_manager._get_user_by_user_email(user_email)
#     if user:
#         if is_password_correct(
#             unhashed_user_password=unhashed_user_password,
#             hashed_user_password=user.hashed_user_password,
#         ):
#             return user
#         else:
#             return None
#     else:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Failed to authenticate user {user_email} because they are not a known user.",
#         )


def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
    pass


def _get_hash_of_password(self, unhashed_user_password: SecretStr) -> SecretStr:
    return SecretStr(self.pwd_context.hash(unhashed_user_password.get_secret_value()))


def is_password_correct(
    unhashed_user_password: SecretStr, hashed_user_password: SecretStr
) -> bool:
    return pwd_context.verify(
        unhashed_user_password.get_secret_value(),
        hashed_user_password.get_secret_value(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        """
        we do this because the `finally` clause will *always* be run, even if there's an
        error somewhere during the `yield`
        """
        global users_manager
        users_manager = await UsersManagerAsync()  # type: ignore[misc]
        yield  # everything above the yield is for startup, everything after is for shutdown
    finally:
        assert isinstance(users_manager, UsersManagerAsync)
        await users_manager.end()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/five_users")
async def get_five_users() -> list[RegisteredUser]:
    assert isinstance(users_manager, UsersManagerAsync)
    return await users_manager.get_five_users_async()


# @app.get("/is_email_address_taken")
# async def is_email_address_taken(email_address: str) -> bool:
#     assert isinstance(users_manager, UsersManagerAsync)
#     return await users_manager.is_email_address_taken(email_address)


@app.post("/user")
async def create_user(new_user_details: RegistrationAttempt) -> RegisteredUser:
    assert isinstance(users_manager, UsersManagerAsync)
    return await users_manager.create_user(new_user_details)


# class ClientSession(BaseModel):
#     client_session_id: str
#     user_id: str | None


# class RegisteredUserClientSession(ClientSession):
#     user_id: str


# class ClientSessionsManager:
#     def __init__(self) -> None:
#         self.active_client_sessions_by_client_id: dict[str, ClientSession] = {}
#         self.users_manager = UsersManager()

#     def add_new_client_session(self, client_session_id: str, user_id: str) -> bool:
#         if client_session_id not in self.active_client_sessions_by_client_id.keys():
#             # just gonna trust that the user_id supplied by the client is really theirs
#             # TODO authenticate or something
#             user = self.users_manager.get_user(user_id)
#             if user:
#                 self.active_client_sessions_by_client_id[client_session_id] = (
#                     RegisteredUserClientSession(
#                         client_session_id=client_session_id, user_id=user_id
#                     )
#                 )
#                 # self.users_manager.start_user(user)
#                 return True
#             else:
#                 # this shouldn't happen, right? maybe this is where we tell the client
#                 # that the user doesn't exist (anymore?)
#                 pass
#         else:
#             print(
#                 f"uh what? duplicate client session id? {client_session_id=} {user_id=}"
#             )
#         return False

#     def _is_user_active(self, user_id: str) -> bool:
#         active_users = set(
#             client_session.user_id
#             for client_session in self.active_client_sessions_by_client_id.values()
#         )
#         return user_id in active_users

#     def end_client_session(self, client_session_id: str) -> None:
#         client_session = self.active_client_sessions_by_client_id.get(client_session_id)
#         if client_session:
#             user_id = client_session.user_id
#             self.active_client_sessions_by_client_id.pop(client_session_id)
#             if user_id and not self._is_user_active(user_id):
#                 user = self.users_manager.get_user(user_id)
#                 if user:
#                     # self.users_manager.stop_user(user)
#                     pass
#         else:
#             # TODO log something?
#             pass

#     # def _format_chat_history_as_list_of_messages(
#     #     self, chat_history: ChatMessageHistory, client_id: str
#     # ) -> list[Message]:
#     #     formatted_chat_history: list[Message] = []
#     #     for message in chat_history.messages:
#     #         assert isinstance(message.content, str)
#     #         if isinstance(message, AIMessage):
#     #             formatted_chat_history.append(GptHomeMessage(text=message.content))
#     #         elif isinstance(message, HumanMessage):
#     #             formatted_chat_history.append(
#     #                 ClientMessage(text=message.content, senderId=client_id)
#     #             )
#     #         else:
#     #             raise Exception(
#     #                 f"Unexpected message type: {message=}. Skipping the message."
#     #             )
#     #     return formatted_chat_history

#     def ask_clients_gpt_home(self, client_message: ClientMessage) -> list[Message]:
#         client_session = self.active_client_sessions_by_client_id.get(
#             client_message.sender_id
#         )
#         if client_session and client_session.user_id:
#             user = self.users_manager.get_user(client_session.user_id)
#             if user:
#                 return []
#                 # return user.ask_gpt_home(client_message.text)
#         return [
#             GptHomeSystemMessage(text=f"invalid client id: {client_message.sender_id=}")
#         ]


# cm = ClientSessionsManager()


class CreateUserRequestBody(BaseModel):
    ai_name: str
    human_name: str
    user_email: str
    user_password: str


# @app.post("/user")
# async def create_user(
#     create_user_request_body: CreateUserRequestBody,
# ) -> RegisteredUser:
#     assert users_manager
#     return await users_manager.create_user(
#         user_email=create_user_request_body.user_email,
#         user_password=create_user_request_body.user_password,
#         human_name=create_user_request_body.human_name,
#         ai_name=create_user_request_body.ai_name,
#     )


# class DeleteUserRequestBody(BaseModel):
#     user_id: str


# @app.delete("/user")
# def delete_user(delete_user_request_body: DeleteUserRequestBody) -> None:
#     users_manager.delete_user(user_id=delete_user_request_body.user_id)


# @app.get("/chats")
# def get_users_chats(user_id: str, start: int, end: int) -> list[ChatPreview]:
#     if users_manager.get_user(user_id):
#         return users_manager.get_user_chat_previews(user_id, start, end)
#     return []


# class CreateClientSessionResponseBody(BaseModel):
#     ready: bool


# @app.post("/registered_user_client_session")
# def create_client_session(
#     client_session_request_body: RegisteredUserClientSession,
# ) -> CreateClientSessionResponseBody:
#     # TODO return something sensible based on whether the user_id is valid
#     ready = cm.add_new_client_session(
#         client_session_id=client_session_request_body.client_session_id,
#         user_id=client_session_request_body.user_id,
#     )
#     return CreateClientSessionResponseBody(ready=ready)


# @app.post("/ask_gpt_home")
# def ask_gpt_home(client_message: ClientMessage) -> list[Message]:
#     return cm.ask_clients_gpt_home(client_message)


# @app.delete("/registered_user_client_session")
# def end_client_session(
#     end_client_session_request_body: ClientSession,
# ) -> None:
#     cm.end_client_session(
#         client_session_id=end_client_session_request_body.client_session_id
#     )


# @app.post("/_inspect")
# def _inspect() -> None:
#     breakpoint()


def main() -> None:
    """
    Don't ask why, but this function needs to be beneath all the endpoint definitions.
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
