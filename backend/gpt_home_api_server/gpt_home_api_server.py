from dataclasses import dataclass
import json
from typing import Any
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from user_management.user_management import GptHomeUserAttributes, UsersManager

from .server_commons import (
    ClientMessage,
    GptHomeMessage,
    GptHomeSystemMessage,
    Message,
)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class ClientSession(BaseModel):
    client_session_id: str
    user_id: str | None


class RegisteredUserClientSession(ClientSession):
    user_id: str


class ClientSessionsManager:
    def __init__(self) -> None:
        self.active_client_sessions_by_client_id: dict[str, ClientSession] = {}
        self.users_manager = UsersManager()

    def add_new_client_session(self, client_session_id: str, user_id: str) -> None:
        if client_session_id not in self.active_client_sessions_by_client_id.keys():
            # just gonna trust that the user_id supplied by the client is really theirs
            # TODO authenticate or something
            user = self.users_manager.get_user(user_id)
            if user:
                self.active_client_sessions_by_client_id[client_session_id] = (
                    RegisteredUserClientSession(
                        client_session_id=client_session_id, user_id=user_id
                    )
                )
                self.users_manager.start_user(user)
            else:
                # this shouldn't happen, right? maybe this is where we tell the client
                # that the user doesn't exist (anymore?)
                pass
        else:
            print(
                f"uh what? duplicate client session id? {client_session_id=} {user_id=}"
            )

    def _is_user_active(self, user_id: str) -> bool:
        active_users = set(
            client_session.user_id
            for client_session in self.active_client_sessions_by_client_id.values()
        )
        return user_id in active_users

    def end_client_session(self, client_session_id: str) -> None:
        client_session = self.active_client_sessions_by_client_id.get(client_session_id)
        if client_session:
            user_id = client_session.user_id
            self.active_client_sessions_by_client_id.pop(client_session_id)
            if user_id and not self._is_user_active(user_id):
                user = self.users_manager.get_user(user_id)
                if user:
                    self.users_manager.stop_user(user)
        else:
            # TODO log something?
            pass

    # def _format_chat_history_as_list_of_messages(
    #     self, chat_history: ChatMessageHistory, client_id: str
    # ) -> list[Message]:
    #     formatted_chat_history: list[Message] = []
    #     for message in chat_history.messages:
    #         assert isinstance(message.content, str)
    #         if isinstance(message, AIMessage):
    #             formatted_chat_history.append(GptHomeMessage(text=message.content))
    #         elif isinstance(message, HumanMessage):
    #             formatted_chat_history.append(
    #                 ClientMessage(text=message.content, senderId=client_id)
    #             )
    #         else:
    #             raise Exception(
    #                 f"Unexpected message type: {message=}. Skipping the message."
    #             )
    #     return formatted_chat_history

    def ask_clients_gpt_home(
        self, client_message: ClientMessage
    ) -> list[GptHomeMessage]:
        client_session = self.active_client_sessions_by_client_id.get(
            client_message.sender_id
        )
        if client_session and client_session.user_id:
            user = self.users_manager.get_user(client_session.user_id)
            if user:
                return [
                    GptHomeMessage(text=msg)
                    for msg in user.ask_gpt_home(client_message.text)
                ]
        return [
            GptHomeSystemMessage(text=f"invalid client id: {client_message.sender_id=}")
        ]


client_sessions_manager = ClientSessionsManager()


@app.get("/users")
def get_users() -> list[GptHomeUserAttributes]:
    return client_sessions_manager.users_manager.get_users()


class CreateUserRequestBody(BaseModel):
    ai_name: str
    human_name: str


@app.post("/user")
def create_user(
    create_user_request_body: CreateUserRequestBody,
) -> GptHomeUserAttributes:
    return client_sessions_manager.users_manager.create_user(
        ai_name=create_user_request_body.ai_name,
        human_name=create_user_request_body.human_name,
    )


@dataclass
class GptHomeServerClientConnection:
    client_id: str
    client_websocket: WebSocket
    user_id: str | None = None


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, GptHomeServerClientConnection] = {}

    async def connect(self, new_client_websocket: WebSocket) -> str:
        # Accept the connection
        # Generate and assign the client an ID
        new_client_id = f"client-session-{str(uuid.uuid4())}"
        self.active_connections[new_client_id] = GptHomeServerClientConnection(
            client_id=new_client_id,
            client_websocket=new_client_websocket,
        )
        # Tell the client that we're now connected. This is a special message, so we're
        # not using self.send_message_to(...) here
        await new_client_websocket.accept()
        await new_client_websocket.send_json(
            {"connection_status": "connection_successful", "id": new_client_id},
        )
        # chat_history = Messages(response.json())
        # for message in chat_history.root:
        #     await self.send_message_to(new_client_id, message)
        return new_client_id

    async def disconnect(self, client_id_or_websocket: str | WebSocket) -> str:
        if isinstance(client_id_or_websocket, str):
            disconnected_client_id = client_id_or_websocket
        else:
            try:
                client_websocket = client_id_or_websocket
                disconnected_client_id = self.get_client_id_by_websocket(
                    client_websocket
                )
            except Exception:
                # log.warn(
                #     f"Unexpectedly failed to find client id: {client_websocket=}\n"
                #     "Going to ignore this and move on..."
                # )
                return ""
        client_sessions_manager.end_client_session(
            client_session_id=disconnected_client_id
        )
        self.active_connections.pop(disconnected_client_id)
        return disconnected_client_id

    def get_clients(self) -> dict[str, GptHomeServerClientConnection]:
        return self.active_connections

    def get_client_by_id(self, client_id: str) -> GptHomeServerClientConnection | None:
        return self.active_connections.get(client_id)

    def get_client_id_by_websocket(self, client_websocket: WebSocket) -> str:
        for id, websocket in self.active_connections.items():
            if websocket == client_websocket:
                return id
        raise Exception(f"Unexpectedly failed to find client id: {client_websocket=}")

    async def send_custom_message_to(self, client_id, json: dict[str, Any]) -> None:
        client = self.get_client_by_id(client_id)
        if client:
            await client.client_websocket.send_json(json)

    async def send_message_to(self, client_id: str, message: Message) -> None:
        """
        Parameters
        ----------
        client_id : str
        message : Message

        Returns
        -------
        bool
            False iff the client ID isn't valid, i.e., they aren't a known client
        """
        client = self.get_client_by_id(client_id)
        if client:
            await client.client_websocket.send_text(message.model_dump_json())
        else:
            raise Exception(
                f"Tried to send a message to an unknown client: {client_id=}, {message=}"
            )

    async def _handle_client_system_message(
        self, client_id: str, client_message: ClientMessage
    ) -> None:
        if client_message.text.startswith("start_chat "):
            # start_chat <user_id>
            user_id = client_message.text.split(" ")[1]
            active_server_client_connection = self.active_connections.get(client_id)
            if active_server_client_connection:
                active_server_client_connection.user_id = user_id
                # TODO return something sensible based on whether the user_id is valid
                client_sessions_manager.add_new_client_session(
                    client_session_id=client_id,
                    user_id=user_id,
                )

    async def acknowledge_and_reply_to_client_message(
        self, client_id: str, client_message: ClientMessage
    ) -> None:
        if (
            client_message.sender_id == f"{client_id}_system"
        ):  # TODO make a dedicated class for this
            await self._handle_client_system_message(client_id, client_message)
        else:
            # forward the message to gpt_home
            gpt_home_messages_from_response = (
                client_sessions_manager.ask_clients_gpt_home(client_message)
            )
            for gpt_home_message in gpt_home_messages_from_response:
                # TODO there's only one message, so this loop is ok. later I'll have to ensure
                # that they get sent in the correct order (or that the order is encoded in
                # the messages somehow, e.g. timestamps)
                await connection_manager.send_message_to(client_id, gpt_home_message)


connection_manager = ConnectionManager()


@app.websocket("/chat")
async def websocket_endpoint(client_websocket: WebSocket) -> None:
    # Accept the connection from the client
    client_id = await connection_manager.connect(client_websocket)
    try:
        await connection_manager.send_custom_message_to(
            client_id=client_id, json={"client_id": client_id}
        )
        while True:
            # Receive the message from the client
            data = json.loads(await client_websocket.receive_text())
            client_message = ClientMessage(**data)
            await connection_manager.acknowledge_and_reply_to_client_message(
                client_id, client_message
            )
    except WebSocketDisconnect:
        # This means the user disconnected, e.g., closed the browser tab
        await connection_manager.disconnect(client_id)


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
