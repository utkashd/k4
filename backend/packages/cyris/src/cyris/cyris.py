import os
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import AsyncGenerator, Literal, NotRequired, TypedDict

from litellm import (  # type: ignore[attr-defined]
    acompletion,
    get_max_tokens,
    get_model_cost_map,
    model_cost_map_url,
    token_counter,
)
from litellm.types.utils import ModelResponseStream
from utils import time_expiring_lru_cache


class CyrisSupportedLlmProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    # google
    # azure


@dataclass
class LlmProviderConfig:
    openai_api_key: str | None
    anthropic_api_key: str | None
    ollama_api_host: str | None


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
        openai_api_key = os.environ.get("CYRIS_OPENAI_API_KEY")
        if not openai_api_key:
            raise Exception("env var `CYRIS_OPENAI_API_KEY` is not defined")

        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.default_model = ""
        self.configured_providers: list[CyrisSupportedLlmProvider] = []
        self.models: dict[str, ModelSupportedByCyris] = {}

    @staticmethod
    @time_expiring_lru_cache(max_age_seconds=60 * 10, max_size=1)
    def get_model_metadata_by_model_name() -> dict:  # type: ignore
        model_metadata_by_model_name = get_model_cost_map(url=model_cost_map_url)
        assert isinstance(model_metadata_by_model_name, dict)
        return model_metadata_by_model_name

    @staticmethod
    @lru_cache(maxsize=1)  # we should only have to compute this once
    def get_available_models() -> dict[str, list[str]]:
        available_models: dict[str, list[str]] = defaultdict(list)
        model_metadata_by_model_name = Cyris.get_model_metadata_by_model_name()
        # TODO refactor to avoid assertions
        for model_name, model_metadata in model_metadata_by_model_name.items():
            assert isinstance(model_name, str)
            assert isinstance(model_metadata, dict)
            if model_metadata.get("mode") in ("chat", "completion"):
                available_models[
                    model_metadata.get("litellm_provider") or "misc"
                ].append(model_name)
        return available_models

    def get_configured_providers(self) -> list[CyrisSupportedLlmProvider]:
        return self.configured_providers

    def add_llm_model(
        self,
        llm_provider: CyrisSupportedLlmProvider,
        llm_model: str,
        provider_config: LlmProviderConfig,
    ) -> None:
        if llm_provider not in self.configured_providers:
            self.configured_providers.append(llm_provider)

        if len(self.models) == 0:
            self.default_model = llm_model

        self.models[llm_model] = ModelSupportedByCyris(
            name=llm_model, max_tokens=get_max_tokens(llm_model)
        )

    def do_chat_messages_have_too_many_tokens(
        self, complete_chat: list[ChatMessage], model: str = ""
    ) -> tuple[bool, int, int]:
        # this implementation is nice because we could easily overwrite it to, e.g.,
        # support "infinite" chat (FIFO queue)
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
