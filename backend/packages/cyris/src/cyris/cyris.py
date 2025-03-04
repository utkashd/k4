import os
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, NotRequired, TypedDict

from cyris.llm_provider_management import LlmProviderManager
from litellm import (  # type: ignore[attr-defined]
    acompletion,
    get_max_tokens,
    token_counter,
)
from litellm.types.utils import ModelResponseStream


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    unmodified_content: NotRequired[str]


@dataclass
class ModelSupportedByCyris:
    name: str
    max_tokens: int | None


class Cyris:
    def __init__(self) -> None:
        self.default_model = "gpt-4o-mini"

    def do_chat_messages_have_too_many_tokens(
        self, complete_chat: list[ChatMessage], model: str = ""
    ) -> tuple[bool, int, int]:
        if not model:
            model = self.default_model
        max_tokens = self.models[model].max_tokens
        if max_tokens:
            num_tokens = token_counter(model=model, messages=list(complete_chat))
            return num_tokens > max_tokens, num_tokens, max_tokens
        return (
            False,
            0,
            -1,
        )

    async def ask_stream(
        self, messages: list[ChatMessage], model: str = ""
    ) -> AsyncGenerator[str | None, None]:
        if not model:
            model = self.default_model
        async for chunk in await acompletion(
            model=model,
            messages=messages,
            stream=True,
        ):
            if not isinstance(chunk, ModelResponseStream):
                raise Exception("Unexpected response type", chunk)
            if len(chunk.choices) != 1:
                raise Exception("Unexpected number of choices in the chunk", chunk)
            if not isinstance(chunk.choices[0].delta.content, str | None):
                raise Exception("Unexpected content type", chunk)
            yield chunk.choices[0].delta.content

    async def ask(self, messages: list[ChatMessage], model: str = "") -> str:
        if not model:
            model = self.default_model
        response = await acompletion(model=model, messages=messages)
        if not isinstance(response.choices[0].message.content, str):
            raise Exception(
                f"unexpected response type: {response.choices[0].message.content=}"
            )
        return response.choices[0].message.content
