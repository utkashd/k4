import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from backend_commons.messages import (
    ClientMessage,
    CyrisConfirmingReceiptOfClientMessage,
    CyrisMessage,
    Message,
)
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from message_management import MessagesManager
from rich.logging import RichHandler


@dataclass(frozen=True)
class CyrisServerClientConnection:
    session_id: uuid.UUID
    session_websocket: WebSocket


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")


class ConnectionManager:
    """
    TODO switch to Redis for session storage. Will be required (ish) if there are
    multiple deployed instances of this server
    """

    def __init__(self) -> None:
        self.active_connections_by_user_id: dict[
            int, set[CyrisServerClientConnection]
        ] = defaultdict(set)
        self.messages_manager: MessagesManager = MessagesManager()

    async def connect(self, new_client_websocket: WebSocket, user_id: int) -> uuid.UUID:
        # Accept the connection
        await new_client_websocket.accept()
        session_id = uuid.uuid4()
        # Tell the client that we're now connected. This is a special message, so we're
        # not using self.send_message_to(...) here.
        await new_client_websocket.send_json(
            {
                "connection_status": "connection_successful",
                "session_id": str(session_id),
            },
        )
        # Generate and assign the client an ID
        # IMPORTANT to do this last, otherwise we may be adding a socket that has
        # already disconnected
        self.active_connections_by_user_id[user_id].add(
            CyrisServerClientConnection(
                session_id=session_id, session_websocket=new_client_websocket
            )
        )
        return session_id

    async def disconnect(self, user_id: int, session_id: uuid.UUID) -> None:
        for connection in self.active_connections_by_user_id[user_id]:
            if connection.session_id == session_id:
                connection_to_remove = connection
                break
        self.active_connections_by_user_id[user_id].remove(connection_to_remove)

    async def send_custom_message_to_user(
        self, user_id: int, json: dict[str, Any]
    ) -> None:
        connections = self.active_connections_by_user_id[user_id]
        dropped_connections: set[CyrisServerClientConnection] = set()
        for connection in connections:
            if (
                connection.session_websocket.application_state
                == WebSocketState.CONNECTED
            ):
                await connection.session_websocket.send_json(json)
            else:
                dropped_connections.add(connection)
        for connection in dropped_connections:
            await self.disconnect(user_id, connection.session_id)

    async def send_message_to_user(self, user_id: int, message: Message) -> None:
        await self.send_custom_message_to_user(user_id, message.model_dump(mode="json"))

    async def save_and_acknowledge_and_reply_to_client_message(
        self, user_id: int, client_message: ClientMessage
    ) -> None:
        # tell the client that we received their message by sending it back to them
        # forward the message to cyris
        # await self.messages_manager.save_client_message_to_db(
        #     chat_id=client_message.chat_id, user_id=user_id, text=client_message.text
        # )

        async def acknowledge_message_receipt(
            user_id: int, client_message: ClientMessage
        ) -> None:
            acknowledge_message = CyrisConfirmingReceiptOfClientMessage(
                client_generated_message_uuid=client_message.client_generated_message_uuid
            )
            await self.send_custom_message_to_user(
                user_id, json=acknowledge_message.model_dump(mode="json")
            )

        await acknowledge_message_receipt(user_id, client_message)
        await self.send_message_to_user(user_id, message=CyrisMessage(text="sup homie"))
