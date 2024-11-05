from collections import defaultdict
import logging
from rich.logging import RichHandler
from typing import Any
from backend_commons.messages import (
    ClientMessage,
    GptHomeConfirmingReceiptOfClientMessage,
    GptHomeMessage,
    Message,
)
import uuid
from dataclasses import dataclass
from fastapi import WebSocket

from message_management import MessagesManager


@dataclass
class GptHomeServerClientConnection:
    session_id: uuid.UUID
    session_websocket: WebSocket


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class ConnectionManager:
    """
    TODO switch to Redis for session storage. Will be required (ish) if there are
    multiple deployed instances of this server
    """

    def __init__(self) -> None:
        self.active_connections_by_user_id: dict[
            int, set[GptHomeServerClientConnection]
        ] = defaultdict(set)
        self.messages_manager: MessagesManager = MessagesManager()

    async def connect(self, new_client_websocket: WebSocket, user_id: int) -> uuid.UUID:
        # Accept the connection
        # Generate and assign the client an ID
        session_id = uuid.uuid4()
        self.active_connections_by_user_id[user_id].add(
            GptHomeServerClientConnection(
                session_id=session_id, session_websocket=new_client_websocket
            )
        )
        # Tell the client that we're now connected. This is a special message, so we're
        # not using self.send_message_to(...) here
        await new_client_websocket.accept()
        await new_client_websocket.send_json(
            {"connection_status": "connection_successful", "id": session_id},
        )
        # chat_history = Messages(response.json())
        # for message in chat_history.root:
        #     await self.send_message_to(session_id, message)
        return session_id

    async def disconnect(self, user_id: int, session_id: uuid.UUID):
        for connection in self.active_connections_by_user_id[user_id]:
            if connection.session_id == session_id:
                connection_to_remove = connection
                break
        self.active_connections_by_user_id[user_id].remove(connection_to_remove)

    async def send_custom_message_to_user(self, user_id: int, json: dict[str, Any]):
        connections = self.active_connections_by_user_id[user_id]
        for connection in connections:
            await connection.session_websocket.send_json(json)

    async def send_message_to_user(self, user_id: int, message: Message):
        connections = self.active_connections_by_user_id[user_id]
        for connection in connections:
            await connection.session_websocket.send_json(message.model_dump_json())

    async def save_and_acknowledge_and_reply_to_client_message(
        self, user_id: int, client_message: ClientMessage
    ) -> None:
        # tell the client that we received their message by sending it back to them
        # forward the message to gpt_home
        await self.messages_manager.save_client_message_to_db(
            chat_id=client_message.chat_id, user_id=user_id, text=client_message.text
        )

        async def acknowledge_message_receipt(
            user_id: int, client_message: ClientMessage
        ):
            acknowledge_message = GptHomeConfirmingReceiptOfClientMessage(
                client_generated_uuid=client_message.client_generated_uuid
            )
            await self.send_custom_message_to_user(
                user_id, json=acknowledge_message.model_dump()
            )

        await acknowledge_message_receipt(user_id, client_message)
        await self.send_message_to_user(
            user_id, message=GptHomeMessage(text="sup homie")
        )
