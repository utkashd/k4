import os
from functools import lru_cache
from typing import AsyncGenerator, Literal, NamedTuple, NotRequired, TypedDict

from cyris.llm_provider_management import CyrisLlmProvider, LlmProviderManager
from litellm import (  # type: ignore[attr-defined]
    acompletion,
    get_max_tokens,
    moderation,
    token_counter,
)
from litellm.types.utils import ModelResponseStream


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
    unmodified_content: NotRequired[str]


class ChatValidityInformation(NamedTuple):
    will_ask_succeed: bool
    failure_detail: str = ""


DEFAULT_LLM_PROVIDER = CyrisLlmProvider.OPENAI
DEFAULT_MODEL = "gpt-4o-mini"


@lru_cache(maxsize=20)
def get_max_tokens_cached(model: str) -> int | None:
    """
    `None` indicates the model has an unlimited context window, I guess?
    """
    return get_max_tokens(model)


class Cyris:
    def __init__(self) -> None:
        self.llm_provider_manager = LlmProviderManager()

    def will_ask_succeed_with_detail(
        self,
        complete_chat: list[ChatMessage],
        llm_provider: CyrisLlmProvider,
        model: str,
    ) -> ChatValidityInformation:
        llm_provider_is_setup = self.llm_provider_manager.is_provider_configured(
            llm_provider=llm_provider
        )
        if not llm_provider_is_setup:
            return ChatValidityInformation(
                will_ask_succeed=False,
                failure_detail=f"{llm_provider=} has not been set up.",
            )

        max_tokens = get_max_tokens_cached(model)
        num_tokens = token_counter(model=model, messages=list(complete_chat))
        if max_tokens and num_tokens > max_tokens:
            return ChatValidityInformation(
                will_ask_succeed=False,
                failure_detail=f"Chat exceeds maximum allowed context window for this model: {num_tokens=} {max_tokens=}",
            )

        if os.environ.get("OPENAI_API_KEY"):
            flagged_values = (
                result.flagged
                for result in moderation(
                    input=complete_chat[-1]["content"], model="omni-moderation-latest"
                ).results
            )
            if any(flagged_values):
                return ChatValidityInformation(
                    will_ask_succeed=False,
                    failure_detail=f"Your input `{complete_chat[-1]['content']}` was flagged for harmful content by OpenAI's moderation endpoint",
                )

        return ChatValidityInformation(
            will_ask_succeed=True,
        )

    async def ask_stream(
        self,
        messages: list[ChatMessage],
        model: str,
    ) -> AsyncGenerator[str | None, None]:
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

    # # TODO 4587: figure out if this is worth keeping
    # async def ask(
    #     self, messages: list[ChatMessage], llm_provider: CyrisLlmProvider, model: str
    # ) -> str:
    #     response = await acompletion(model=model, messages=messages)
    #     if not isinstance(response.choices[0].message.content, str):
    #         raise Exception(
    #             f"unexpected response type: {response.choices[0].message.content=}"
    #         )
    #     return response.choices[0].message.content
