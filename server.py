"""
Got most of this from a medium post: https://medium.com/@abderraoufbenchoubane/building-a-real-time-websocket-server-using-python-d557c43a3ff3
"""

import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid
import json
from rich import print as rich_print
from gpt_home.errors import GptHomeError

log = logging.getLogger("gpt_home")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, new_client_websocket: WebSocket) -> str:
        await new_client_websocket.accept()
        new_client_id = str(uuid.uuid4())
        self.active_connections[new_client_id] = new_client_websocket
        await self.send_message_to(
            new_client_websocket, json.dumps({"type": "connect", "id": new_client_id})
        )
        return new_client_id

    def disconnect(self, client: WebSocket | str) -> str:
        if isinstance(client, str):
            disconnected_client_id = client
        else:
            try:
                disconnected_client_id = self.get_client_id_by_websocket(client)
            except GptHomeError:
                log.exception(f"Unexpectedly failed to find client id: {client=}")
                rich_print("exception uh oh")
                return ""
        self.active_connections.pop(disconnected_client_id)
        return disconnected_client_id

    def get_clients(self) -> dict[str, WebSocket]:
        """
        Returns a dict mapping client IDs to client WebSockets

        Returns
        -------
        dict[str, WebSocket]
            id -> WebSocket
        """
        return self.active_connections

    def get_client_id_by_websocket(self, client_websocket: WebSocket) -> str:
        for id, websocket in self.active_connections.items():
            if websocket == client_websocket:
                return id
        raise GptHomeError(
            f"Unexpectedly failed to find client id: {client_websocket=}"
        )

    async def send_message_to(self, client: WebSocket | str, message: str) -> None:
        """
        Sends a message to the provided client.

        Parameters
        ----------
        client : WebSocket | str
            The client's Websocket or the client's ID
        message : str
            The message to send
        """
        if isinstance(client, str):
            client = self.active_connections[client]
        await client.send_text(message)

    async def broadcast(self, message: str) -> None:
        for connection in self.active_connections.values():
            await self.send_message_to(connection, message)


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
            rich_print(f"received: {data=}")
            await connection_manager.send_message_to(
                client_websocket,
                json.dumps({"text": data["text"], "senderId": client_id}),
            )
            # log.info(f"Received: {data=}")
            # Send a message back
            await connection_manager.send_message_to(
                client_websocket,
                json.dumps(
                    {
                        "text": "nm, u?",
                        "senderId": "gpt_home",
                    }
                ),
            )
    except WebSocketDisconnect:
        # This means the user disconnected, e.g., closed the browser tab
        connection_manager.disconnect(client_id)
