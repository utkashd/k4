import os
from typing import AsyncGenerator, Literal, NotRequired, TypedDict

from litellm import acompletion, get_max_tokens, token_counter
from litellm.types.utils import ModelResponseStream


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    unmodified_content: NotRequired[str]


class Cyris:
    def __init__(self) -> None:
        openai_api_key = os.environ.get("CYRIS_OPENAI_API_KEY")
        if not openai_api_key:
            raise Exception("env var `CYRIS_OPENAI_API_KEY` is not defined")

        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.model = "gpt-4o-mini"
        self.max_tokens = get_max_tokens(self.model)

    def do_chat_messages_have_too_many_tokens(
        self,
        complete_chat: list[ChatMessage],
    ) -> tuple[bool, int, int]:
        # this implementation is nice because we could easily overwrite it to, e.g.,
        # support "infinite" chat (FIFO queue)
        if self.max_tokens:
            num_tokens = token_counter(model=self.model, messages=complete_chat)
            return num_tokens > self.max_tokens, num_tokens, self.max_tokens
        return (
            False,
            0,
            -1,
        )

    async def ask_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncGenerator[str | None, None]:
        async for chunk in await acompletion(
            model=self.model,
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
