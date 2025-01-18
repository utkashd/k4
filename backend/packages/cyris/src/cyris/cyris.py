import os
import logging
from typing import AsyncGenerator
from backend_commons.messages import MessageInDb
from litellm import acompletion
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

    async def ask(
        self, new_msg: MessageInDb, chat_history: list[MessageInDb]
    ) -> list[str]:
        # lm.history = [] # TODO figure out how to not retain history
        history: list[dict[str, str]] = []
        for history_message in chat_history:
            history.append(
                {
                    "role": "user" if history_message.user_id else "assistant",
                    "content": history_message.text,
                }
            )
        history.append({"role": "user", "content": new_msg.text})
        response = await acompletion(model="gpt-4o-mini", messages=history)
        return [response.choices[0].message.content]

    async def ask_stream(
        self, new_msg: MessageInDb, chat_history: list[MessageInDb]
    ) -> AsyncGenerator[str | None, None]:
        history: list[dict[str, str]] = []
        for history_message in chat_history:
            history.append(
                {
                    "role": "user" if history_message.user_id else "assistant",
                    "content": history_message.text,
                }
            )
        history.append({"role": "user", "content": new_msg.text})

        async for chunk in await acompletion(
            model="gpt-4o-mini", messages=history, stream=True
        ):
            if not isinstance(chunk, ModelResponseStream):
                raise Exception("Unexpected response type", chunk)
            if len(chunk.choices) != 1:
                raise Exception("Unexpected number of choices in the chunk", chunk)
            if not isinstance(chunk.choices[0].delta.content, str | None):
                raise Exception("Unexpected content type", chunk)
            yield chunk.choices[0].delta.content
