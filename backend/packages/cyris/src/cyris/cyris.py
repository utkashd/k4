from functools import lru_cache
from typing import AsyncGenerator, Literal, NamedTuple, NotRequired, TypedDict

import litellm
from cyris.llm_provider_management import CyrisLlmProvider, LlmProviderManager
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
    return litellm.get_max_tokens(model)  # type: ignore[attr-defined]


@lru_cache(maxsize=20)
def get_llm_provider_by_model_name(model: str) -> CyrisLlmProvider:
    for llm_provider in CyrisLlmProvider:
        models_of_provider = litellm.models_by_provider.get(llm_provider.value)
        assert isinstance(models_of_provider, list)
        if model in models_of_provider:
            return llm_provider
    raise ValueError(f"Invalid model? {model=}")


class Cyris:
    def __init__(self) -> None:
        self.llm_provider_manager = LlmProviderManager()

    async def setup_llm_providers_from_disk(self) -> None:
        await self.llm_provider_manager.read_and_configure_providers_from_disk_if_file_exists()

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
        if max_tokens:
            num_tokens = litellm.token_counter(  # type: ignore[attr-defined]
                model=model, messages=list(complete_chat)
            )
            if num_tokens > max_tokens:
                return ChatValidityInformation(
                    will_ask_succeed=False,
                    failure_detail=f"Chat exceeds maximum allowed context window for this model: {num_tokens=} {max_tokens=}",
                )

        if self.llm_provider_manager.is_provider_configured(CyrisLlmProvider.OPENAI):
            flagged_values = (
                result.flagged
                for result in litellm.moderation(
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
        def _get_extra_args_for_ollama_or_huggingface() -> dict[str, str]:
            extra_args_for_ollama_or_huggingface: dict[str, str] = {}
            llm_provider = get_llm_provider_by_model_name(model)
            if llm_provider is CyrisLlmProvider.OLLAMA:
                assert self.llm_provider_manager.is_provider_configured(
                    CyrisLlmProvider.OLLAMA
                )
                extra_args_for_ollama_or_huggingface["api_base"] = (
                    self.llm_provider_manager.get_provider_config_else_raise(
                        CyrisLlmProvider.OLLAMA
                    ).environment_variable_value
                )
            elif llm_provider is CyrisLlmProvider.HUGGINGFACE:
                assert self.llm_provider_manager.is_provider_configured(
                    CyrisLlmProvider.HUGGINGFACE
                )
                extra_args_for_ollama_or_huggingface["api_base"] = (
                    self.llm_provider_manager.get_provider_config_else_raise(
                        CyrisLlmProvider.HUGGINGFACE
                    ).environment_variable_value
                )
            return extra_args_for_ollama_or_huggingface

        # for char in messages[-1]["content"]:
        #     yield char

        async for chunk in await litellm.acompletion(
            model=model,
            messages=messages,
            stream=True,
            **_get_extra_args_for_ollama_or_huggingface(),
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
