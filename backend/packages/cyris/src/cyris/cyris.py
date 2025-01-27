import logging
import os
from typing import AsyncGenerator, Literal, TypedDict

from litellm import acompletion, get_max_tokens, token_counter
from litellm.types.utils import ModelResponseStream
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class Cyris:
    def __init__(self) -> None:
        openai_api_key = os.environ.get("CYRIS_OPENAI_API_KEY")
        if not openai_api_key:
            raise Exception("env var `CYRIS_OPENAI_API_KEY` is not defined")

        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.model = "gpt-4o-mini"
        self.max_tokens = get_max_tokens(self.model)

    def does_string_have_too_many_tokens(self, msg: str) -> tuple[bool, int]:
        if self.max_tokens:
            num_tokens = token_counter(
                model=self.model, messages=[{"role": "user", "content": msg}]
            )
            return (num_tokens > self.max_tokens, num_tokens)
        return False, 0

    def do_messages_have_too_many_tokens(
        self,
        new_msg: str,
        chat_history: list[ChatMessage],
    ) -> tuple[bool, int, list[ChatMessage]]:
        # this implementation is nice because we could easily overwrite it to, e.g.,
        # support "infinite" chat (FIFO queue)
        chat_history.append({"role": "user", "content": new_msg})
        if self.max_tokens:
            num_tokens = token_counter(model=self.model, messages=chat_history)
            return num_tokens > self.max_tokens, num_tokens, chat_history
        return False, 0, chat_history

    async def ask_stream(
        self, messages: list[ChatMessage]
    ) -> AsyncGenerator[str | None, None]:
        async for chunk in await acompletion(
            model=self.model, messages=messages, stream=True
        ):
            if not isinstance(chunk, ModelResponseStream):
                raise Exception("Unexpected response type", chunk)
            if len(chunk.choices) != 1:
                raise Exception("Unexpected number of choices in the chunk", chunk)
            if not isinstance(chunk.choices[0].delta.content, str | None):
                raise Exception("Unexpected content type", chunk)
            yield chunk.choices[0].delta.content
