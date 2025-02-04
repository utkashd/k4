from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from backend_commons.messages import MessageInDb
from extendables import hookimpl, hookspec, plugin_manager

from cyris import ChatMessage


@dataclass
class ParamsForAlreadyExistingChat:
    """
    chat_id: `int`
    get_messages_of_chat: GetMessagesOfChatFunctionType
        An async function that accepts a `chat_id` and an optional `limit`, which
        returns a list of chat messages in the DB
    """

    class GetMessagesOfChatFunctionType(Protocol):
        async def __call__(
            self, chat_id: int, limit: int | None = None
        ) -> list[MessageInDb]: ...

    chat_id: int
    get_messages_of_chat: GetMessagesOfChatFunctionType


class GetCompleteChatSpec:
    @hookspec  # type: ignore[misc]
    async def get_complete_chat_for_llm(  # type: ignore[empty-body]
        self,
        new_message_from_user: str,
        existing_chat_params: ParamsForAlreadyExistingChat | None,
    ) -> list[ChatMessage]: ...


def convert_messages_in_db_to_chat_messages(
    chat_history: list[MessageInDb],
) -> list[ChatMessage]:
    return [
        ChatMessage(
            role="user" if msg_in_db.user_id else "assistant",
            content=msg_in_db.text,
        )
        for msg_in_db in chat_history
    ]


class GetCompleteChatImplementationAbstract(ABC):
    @abstractmethod
    @hookimpl  # type: ignore[misc]
    async def get_complete_chat_for_llm(
        self,
        new_message_from_user: str,
        existing_chat_params: ParamsForAlreadyExistingChat | None,
    ) -> list[ChatMessage]:
        """
        Retrieves chat messages and constructs a list of `ChatMessage` which can be passed
        to the LLM.

        Parameters
        ----------
        new_message_from_user : str
            The new message that the user just sent
        existing_chat_params : ParamsForAlreadyExistingChat | None
            If this isn't a new chat, information necessary about the chat, otherwise None

        Returns
        -------
        list[ChatMessage]
            The complete chat, which will be sent to the LLM for response. Last element is the latest message.
        """
        ...


class GetCompleteChatDefaultImplementation(GetCompleteChatImplementationAbstract):
    @hookimpl  # type: ignore[misc]
    async def get_complete_chat_for_llm(
        self,
        new_message_from_user: str,
        existing_chat_params: ParamsForAlreadyExistingChat | None,
    ) -> list[ChatMessage]:
        if not existing_chat_params:
            return [
                ChatMessage(
                    role="user",
                    content=new_message_from_user,
                )
            ]
        else:
            chat_history = await existing_chat_params.get_messages_of_chat(
                existing_chat_params.chat_id, None
            )

            complete_chat = convert_messages_in_db_to_chat_messages(chat_history)
            complete_chat.append(
                ChatMessage(
                    role="user",
                    content=new_message_from_user,
                )
            )
            return complete_chat


async def get_complete_chat_for_llm(
    new_message_from_user: str,
    existing_chat_params: ParamsForAlreadyExistingChat | None,
) -> list[ChatMessage]:
    complete_chats: list[
        list[ChatMessage]
    ] = await plugin_manager.ahook.get_complete_chat_for_llm(
        new_message_from_user=new_message_from_user,
        existing_chat_params=existing_chat_params,
    )
    return complete_chats[0]
