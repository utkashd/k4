import os
from fastapi import FastAPI
from pydantic import BaseModel
from gpt_home import GptHome
from server_commons.server_commons import (
    ClientMessage,
    GptHomeMessage,
    GptHomeSystemMessage,
    Message,
)
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory

app = FastAPI()


class ClientsManager:
    def __init__(self) -> None:
        self.clients: dict[str, GptHome] = {}

    def add_new_client_or_ensure_already_exists(self, client_id: str) -> list[Message]:
        if client_id not in self.clients.keys():
            self.clients[client_id] = GptHome(
                ai_name=os.environ.get("GPT_HOME_AI_NAME") or "GptHome",
                human_name=os.environ.get("GPT_HOME_HUMAN_NAME") or "Human",
                ignore_home_assistant_ssl=os.environ.get("GPT_HOME_HA_IGNORE_SSL")
                or False,
            )
        return self._format_chat_history_as_list_of_messages(
            self.clients[client_id].chat_history, client_id
        )

    def _format_chat_history_as_list_of_messages(
        self, chat_history: ChatMessageHistory, client_id: str
    ) -> list[Message]:
        formatted_chat_history: list[Message] = []
        for message in chat_history.messages:
            assert isinstance(message.content, str)
            if isinstance(message, AIMessage):
                formatted_chat_history.append(GptHomeMessage(text=message.content))
            elif isinstance(message, HumanMessage):
                formatted_chat_history.append(
                    ClientMessage(text=message.content, senderId=client_id)
                )
            else:
                raise Exception(
                    f"Unexpected message type: {message=}. Skipping the message."
                )
        return formatted_chat_history

    def ask_clients_gpt_home(
        self, client_message: ClientMessage
    ) -> list[GptHomeMessage]:
        client_gpt_home = self.clients.get(client_message.senderId)
        if not client_gpt_home:
            return [
                GptHomeSystemMessage(
                    text=f"invalid client id: {client_message.senderId=}"
                )
            ]
        return [GptHomeMessage(text=client_gpt_home.ask_gpt_home(client_message.text))]


cm = ClientsManager()


class ProcessNewClientRequestBody(BaseModel):
    client_id: str


@app.post("/new_client")
def process_new_client(request_body: ProcessNewClientRequestBody) -> list[Message]:
    return cm.add_new_client_or_ensure_already_exists(request_body.client_id)


@app.post("/ask_gpt_home")
def ask_gpt_home(client_message: ClientMessage) -> list[GptHomeMessage]:
    return cm.ask_clients_gpt_home(client_message)


# @app.post("/delete_client")
# def delete_client()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
