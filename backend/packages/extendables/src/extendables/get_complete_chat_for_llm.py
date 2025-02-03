from dataclasses import dataclass
from typing import Awaitable, Callable

import apluggy  # type: ignore[import-untyped,unused-ignore]
from backend_commons.messages import MessageInDb

from cyris import ChatMessage, ModifiedChatMessage

hookspec = apluggy.HookspecMarker("get_complete_chat_for_llm")
hookimpl = apluggy.HookimplMarker("get_complete_chat_for_llm")


@dataclass
class ParamsForAlreadyExistingChat:
    """
    chat_id: `int`
    get_messages_of_chat: `Callable[[int, int | None], Awaitable[list[MessageInDb]]]`
        An async function that accepts a `chat_id` and an optional `limit`, which
        returns a list of chat messages in the DB
    """

    chat_id: int
    get_messages_of_chat: Callable[[int, int | None], Awaitable[list[MessageInDb]]]


class GetCompleteChatSpec:
    @hookspec  # type: ignore[misc]
    async def get_complete_chat_for_llm(  # type: ignore[empty-body]
        self,
        new_message_from_user: str,
        existing_chat_params: ParamsForAlreadyExistingChat | None,
    ) -> list[ChatMessage | ModifiedChatMessage]: ...


class GetCompleteChatDefaultImplementation:
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
        existing_chat_params : ParamsForAlreadyExistingChat | None, optional
            If this isn't a new chat, information necessary about the chat, by default None

        Returns
        -------
        list[ChatMessage]
            The complete chat, which will be sent to the LLM for response. 0th element is
            the earliest message, the last element is the latest message.
        """
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

            complete_chat = convert_messages_in_db_to_chat_messages(chat_history)
            complete_chat.append(
                ChatMessage(
                    role="user",
                    content=new_message_from_user,
                )
            )
            return complete_chat


plugin_manager = apluggy.PluginManager("get_complete_chat_for_llm")
plugin_manager.add_hookspecs(GetCompleteChatSpec)
plugin_manager.register(GetCompleteChatDefaultImplementation())


async def get_complete_chat_for_llm(
    new_message_from_user: str,
    existing_chat_params: ParamsForAlreadyExistingChat | None,
) -> list[ChatMessage | ModifiedChatMessage]:
    complete_chats: list[
        list[ChatMessage | ModifiedChatMessage]
    ] = await plugin_manager.ahook.get_complete_chat_for_llm(
        new_message_from_user=new_message_from_user,
        existing_chat_params=existing_chat_params,
    )
    return complete_chats[0]
