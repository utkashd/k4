import json
import os
from pathlib import Path
import uuid
from ..gpt_home_api_server.messages import (
    ClientMessage,
    GptHomeMessage,
    GptHomeSystemMessage,
    Message,
)
from gpt_home.gpt_home_human import GptHomeHuman
from gpt_home.utils.file_io import (
    get_chat_history_directory_and_chat_history_preview_directory_for_timestamp,
)
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from rich import print as rich_print
from datetime import datetime


class ChatHistory:
    """
    A langchain-compatible chat history that has some extra features (e.g., system messages)
    """

    def __init__(self, gpt_home_user: GptHomeHuman):
        self.langchain_chat_message_history_no_system_messages = ChatMessageHistory()
        self.all_messages_including_system_messages: list[Message] = []
        self.starting_index_of_latest_response = 0
        self.gpt_home_user = gpt_home_user
        self.chat_id = str(uuid.uuid4())

    def _get_chat_history_filename(self) -> str:
        first_message_datetime = datetime.fromtimestamp(
            self.all_messages_including_system_messages[0].time_message_was_sent
        )
        hour = (
            str(first_message_datetime.hour)
            if first_message_datetime.hour >= 10
            else f"0{first_message_datetime.hour}"
        )
        minute = (
            str(first_message_datetime.minute)
            if first_message_datetime.minute >= 10
            else f"0{first_message_datetime.minute}"
        )
        chat_history_filename = f"{hour}-{minute}_{self.chat_id}.json"
        return chat_history_filename

    def save_chat_history_with_system_messages_to_disk(self) -> None:
        """
        Saves the chat history and a preview of the chat history to disk
        """
        if self.all_messages_including_system_messages:
            chat_history_directories = get_chat_history_directory_and_chat_history_preview_directory_for_timestamp(
                self.gpt_home_user.user_id,
                self.all_messages_including_system_messages[0].time_message_was_sent,
            )

            # first we'll save the chat history
            this_chat_history_filepath = Path(
                os.path.join(
                    chat_history_directories.chat_history_directory,
                    self._get_chat_history_filename(),
                )
            )
            chat_history_with_metadata = {
                "chat_id": self.chat_id,
                "time_first_message_was_sent": self.all_messages_including_system_messages[
                    0
                ].time_message_was_sent,
                "time_latest_message_was_sent": self.all_messages_including_system_messages[
                    -1
                ].time_message_was_sent,
                "messages": [
                    msg.model_dump()
                    for msg in self.all_messages_including_system_messages
                ],
            }
            with open(this_chat_history_filepath, "w") as chat_history_file:
                json.dump(chat_history_with_metadata, chat_history_file, indent=4)

            # now we'll generate and save the chat history preview
            this_chat_history_preview_filepath = Path(
                os.path.join(
                    chat_history_directories.chat_history_preview_directory,
                    self._get_chat_history_filename(),
                )
            )
            chat_history_preview = {
                # the preview needs to be small so that reading the file and loading it
                # into memory is fast
                "chat_id": self.chat_id,
                "chat_preview_title": "Placeholder! lol",
                "latest_message": self.all_messages_including_system_messages[
                    -1
                ].model_dump(),
            }
            with open(
                this_chat_history_preview_filepath, "w"
            ) as chat_history_preview_file:
                json.dump(chat_history_preview, chat_history_preview_file, indent=4)

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
