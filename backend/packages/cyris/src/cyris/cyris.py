import os
import logging
from typing import AsyncGenerator
from backend_commons.messages import MessageInDb
from litellm import acompletion, token_counter, get_max_tokens
from litellm.types.utils import ModelResponseStream
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")


class Cyris:
    def __init__(self):
        openai_api_key = os.environ.get("CYRIS_OPENAI_API_KEY")
        if not openai_api_key:
            raise Exception("env var `CYRIS_OPENAI_API_KEY` is not defined")

        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.model = "gpt-4o-mini"
        self.max_tokens = get_max_tokens(self.model)

    def does_string_have_too_many_tokens(self, msg: str) -> tuple[bool, int]:
        num_tokens = token_counter(
            model=self.model, messages=[{"role": "user", "content": msg}]
        )
        return (num_tokens > self.max_tokens, num_tokens)

    def do_messages_have_too_many_tokens(
        self,
        new_msg: str,
        chat_history: list[
            MessageInDb
        ],  # TODO refactor so this doesn't rely on MessageInDb?
    ) -> tuple[bool, int, list[dict[str, str]]]:
        # this implementation is nice because we could easily overwrite it to, e.g.,
        # support "infinite" chat (FIFO queue)
        history: list[dict[str, str]] = []
        for history_message in chat_history:
            history.append(
                {
                    "role": "user" if history_message.user_id else "assistant",
                    "content": history_message.text,
                }
            )
        history.append({"role": "user", "content": new_msg})
        num_tokens = token_counter(model=self.model, messages=history)
        return num_tokens > self.max_tokens, num_tokens, history

    async def ask_stream(
        self, messages: list[dict[str, str]]
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
