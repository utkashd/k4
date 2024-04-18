"""
Got most of this from a medium post:
https://medium.com/@abderraoufbenchoubane/building-a-real-time-websocket-server-using-python-d557c43a3ff3

start frontend with
```bash
cd frontend && npm run dev
```
"""

from dataclasses import dataclass
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid
import json
import requests
from .server_commons import (  # type: ignore[import-untyped] # idk why this is necessary
    ClientMessage,
    GptHomeMessages,
    Message,
    # Messages,
)


log = logging.getLogger("gpt_home")


@dataclass
class GptHomeServerClientConnection:
    client_id: str
    client_websocket: WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, GptHomeServerClientConnection] = {}

    async def connect(self, new_client_websocket: WebSocket) -> str:
        # Accept the connection
        # Generate and assign the client an ID
        new_client_id = f"client-session-{str(uuid.uuid4())}"
        # response = requests.post(
        #     "http://localhost:8000/registered_user_client_session",
        #     json={"client_session_id": new_client_id},
        # )
        self.active_connections[new_client_id] = GptHomeServerClientConnection(
            client_id=new_client_id,
            client_websocket=new_client_websocket,
        )
        # Tell the client that we're now connected. This is a special message, so we're
        # not using self.send_message_to(...) here
        await new_client_websocket.accept()
        await new_client_websocket.send_text(
            json.dumps({"type": "connection_successful", "id": new_client_id}),
        )
        # chat_history = Messages(response.json())
        # for message in chat_history.root:
        #     await self.send_message_to(new_client_id, message)
        return new_client_id

    def disconnect(self, client_id_or_websocket: str | WebSocket) -> str:
        if isinstance(client_id_or_websocket, str):
            disconnected_client_id = client_id_or_websocket
        else:
            try:
                client_websocket = client_id_or_websocket
                disconnected_client_id = self.get_client_id_by_websocket(
                    client_websocket
                )
            except Exception:
                log.exception(
                    f"Unexpectedly failed to find client id: {client_websocket=}\n"
                    "Going to ignore this and move on..."
                )
                return ""
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

    async def acknowledge_and_reply_to_client_message(
        self, client_id: str, client_message: ClientMessage
    ) -> None:
        # tell the client that we received their message by sending it back to them
        await self.send_message_to(client_id, client_message)
        # forward the message to gpt_home
        response = requests.post(
            "http://localhost:8000/ask_gpt_home",
            json=ClientMessage(
                text=client_message.text, senderId=client_id
            ).model_dump(),
        )
        gpt_home_messages_from_response = GptHomeMessages(response.json())
        for gpt_home_message in gpt_home_messages_from_response.root:
            await connection_manager.send_message_to(client_id, gpt_home_message)


app = FastAPI()

connection_manager = ConnectionManager()


@app.websocket("/chat")
async def websocket_endpoint(client_websocket: WebSocket) -> None:
    # Accept the connection from the client
    client_id = await connection_manager.connect(client_websocket)
    try:
        while True:
            # Receive the message from the client
            data = json.loads(await client_websocket.receive_text())
            client_message = ClientMessage(**data)
            await connection_manager.acknowledge_and_reply_to_client_message(
                client_id, client_message
            )
    except WebSocketDisconnect:
        # This means the user disconnected, e.g., closed the browser tab
        connection_manager.disconnect(client_id)


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
