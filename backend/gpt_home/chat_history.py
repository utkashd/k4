import json
import os
from pathlib import Path
import uuid
from backend_commons.messages import (
    ClientMessage,
    GptHomeMessage,
    GptHomeSystemMessage,
    Message,
)
from gpt_home.gpt_home_human import GptHomeHuman
from gpt_home.utils.file_io import get_a_users_directory
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from rich import print as rich_print


class ChatHistory:
    """
    A langchain-compatible chat history that has some extra features (e.g., system messages)
    """

    def __init__(self, gpt_home_user: GptHomeHuman):
        self.langchain_chat_message_history_no_system_messages = ChatMessageHistory()
        self.all_messages_including_system_messages: list[Message] = []
        self.starting_index_of_latest_response = 0
        self.gpt_home_user = gpt_home_user

    def save_chat_history_with_system_messages_to_disk(self) -> None:
        if self.all_messages_including_system_messages:
            directory = get_a_users_directory(self.gpt_home_user.user_id)
            chat_history_filename = Path(
                os.path.join(directory, f"chat_history_{uuid.uuid4()}.json")
            )
            serializable_chat_history = [
                msg.model_dump() for msg in self.all_messages_including_system_messages
            ]
            with open(chat_history_filename, "w") as chat_history_file:
                json.dump(serializable_chat_history, chat_history_file, indent=4)

    def get_chat_history_for_langchain_agent(self) -> list[BaseMessage]:
        return self.langchain_chat_message_history_no_system_messages.messages

    def add_human_message(self, human_message: str) -> None:
        self.langchain_chat_message_history_no_system_messages.add_user_message(
            HumanMessage(name=self.gpt_home_user.human_name, content=human_message)
        )
        self.all_messages_including_system_messages.append(
            ClientMessage(text=human_message, sender_id=self.gpt_home_user.user_id)
        )
        self.starting_index_of_latest_response = len(
            self.all_messages_including_system_messages
        )  # it's now everything after this human message

    def add_gpt_home_message(self, gpt_home_message: str) -> None:
        self.langchain_chat_message_history_no_system_messages.add_ai_message(
            AIMessage(name=self.gpt_home_user.ai_name, content=gpt_home_message)
        )
        self.all_messages_including_system_messages.append(
            GptHomeMessage(text=gpt_home_message)
        )

    def add_gpt_home_system_message(self, gpt_home_system_message: str) -> None:
        self.all_messages_including_system_messages.append(
            GptHomeSystemMessage(text=gpt_home_system_message)
        )
        rich_print(f"\n[italic blue]{gpt_home_system_message}[/italic blue]")

    def get_latest_response(self) -> list[Message]:
        latest_response = self.all_messages_including_system_messages[
            self.starting_index_of_latest_response :
        ]
        return latest_response

    def clear(self) -> None:
        self.langchain_chat_message_history_no_system_messages.clear()
        self.all_messages_including_system_messages.clear()
