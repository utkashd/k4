"""
Got most of this from a medium post:
https://medium.com/@abderraoufbenchoubane/building-a-real-time-websocket-server-using-python-d557c43a3ff3

start frontend with
```bash
cd frontend && npm run dev
```
"""

from dataclasses import dataclass
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid
import json
import aiohttp
import uvicorn
from backend_commons.messages import (
    ClientMessage,
    GptHomeMessages,
    Message,
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
                # log.exception(
                #     f"Unexpectedly failed to find client id: {client_websocket=}\n"
                #     "Going to ignore this and move on..."
                # )
                return ""
        # requests.delete(
        #     "http://localhost:8000/registered_user_client_session",
        #     json={"client_session_id": disconnected_client_id, "user_id": None},
        # )
        async with aiohttp.ClientSession() as session:
            await session.delete(
                "http://localhost:8000/registered_user_client_session",
                json={"client_session_id": disconnected_client_id, "user_id": None},
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
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/registered_user_client_session",
                        json={
                            "client_session_id": client_id,
                            "user_id": user_id,
                        },
                    ) as response:
                        response_json = await response.json()
                        await self.send_custom_message_to(
                            client_id=client_id, json=response_json
                        )

    async def acknowledge_and_reply_to_client_message(
        self, client_id: str, client_message: ClientMessage
    ) -> None:
        if (
            client_message.sender_id == f"{client_id}_system"
        ):  # TODO make a dedicated class for this
            await self._handle_client_system_message(client_id, client_message)
        else:
            # tell the client that we received their message by sending it back to them
            # await self.send_message_to(client_id, client_message)
            # forward the message to gpt_home
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/ask_gpt_home",
                    json=ClientMessage(
                        text=client_message.text, sender_id=client_id
                    ).model_dump(),
                ) as response:
                    gpt_home_messages_from_response = GptHomeMessages(
                        await response.json()
                    )
                    for gpt_home_message in gpt_home_messages_from_response.root:
                        # there's only one message, so this loop is ok. later I'll have to ensure
                        # that they get sent in the correct order (or that the order is encoded in
                        # the messages somehow, e.g. timestamps)
                        await connection_manager.send_message_to(
                            client_id, gpt_home_message
                        )


app = FastAPI()

connection_manager = ConnectionManager()


@app.websocket("/chat")
async def websocket_endpoint(client_websocket: WebSocket) -> None:
    # Accept the connection from the client
    client_id = await connection_manager.connect(client_websocket)
    try:
        # immediately tell them their client id
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
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
