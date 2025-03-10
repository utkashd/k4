import json
import os
from collections import defaultdict
from enum import Enum
from functools import lru_cache
from pathlib import Path

import aiofiles
from litellm import get_model_cost_map, model_cost_map_url  # type: ignore[attr-defined]
from pydantic import BaseModel
from utils import time_expiring_lru_cache


class LlmProviderMetadata(BaseModel):
    environment_variable_name: str


class LlmProviderConfig(BaseModel):
    environment_variable_value: str


class LlmProviderInfo(BaseModel):
    metadata: LlmProviderMetadata
    config: LlmProviderConfig | None


class CyrisLlmProvider(Enum):
    # Important that the strings match the model names used by litellm: see litellm.models_by_provider
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"


LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT: dict[CyrisLlmProvider, LlmProviderInfo] = {
    # TODO write a test that ensures every llm provider is in this dict
    CyrisLlmProvider.OPENAI: LlmProviderInfo(
        metadata=LlmProviderMetadata(environment_variable_name="OPENAI_API_KEY"),
        config=None,
    ),
    CyrisLlmProvider.ANTHROPIC: LlmProviderInfo(
        metadata=LlmProviderMetadata(environment_variable_name="ANTHROPIC_API_KEY"),
        config=None,
    ),
    CyrisLlmProvider.OLLAMA: LlmProviderInfo(
        metadata=LlmProviderMetadata(environment_variable_name="OLLAMA_BASE_URL"),
        config=None,
    ),
    CyrisLlmProvider.OPENROUTER: LlmProviderInfo(
        metadata=LlmProviderMetadata(environment_variable_name="OPENROUTER_API_KEY"),
        config=None,
    ),
    CyrisLlmProvider.HUGGINGFACE: LlmProviderInfo(
        metadata=LlmProviderMetadata(environment_variable_name="HUGGINGFACE_API_KEY"),
        config=None,
    ),
}


class LlmProviderManager:
    def __init__(self) -> None:
        providers_directory = Path.home().joinpath(".cyris/providers")
        providers_directory.mkdir(exist_ok=True, parents=True)
        self._providers_file = providers_directory.joinpath("providers.json")

        self.providers = LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT

    async def read_and_configure_providers_from_disk_if_file_exists(self) -> None:
        if self._providers_file.exists():
            async with aiofiles.open(self._providers_file, mode="r") as file:
                file_contents = await file.read()
            providers_json: dict[str, dict[str, str | None]] = json.loads(file_contents)

            self.providers.clear()
            for provider_name, provider_info in providers_json.items():
                self.providers[CyrisLlmProvider(provider_name)] = (
                    LlmProviderInfo.model_validate(provider_info)
                )

            for llm_provider, llm_provider_info in self.providers.items():
                if llm_provider_info.config:
                    self.configure_provider(  # this repeats work we just did in the previous for-loop but whatever
                        llm_provider=llm_provider,
                        llm_provider_config=llm_provider_info.config,
                    )

    async def _save_providers_to_disk(self) -> None:
        serializable_providers = {}
        for provider_name, provider_info in self.providers.items():
            serializable_providers[provider_name.value] = provider_info.model_dump(
                mode="json"
            )
        async with aiofiles.open(self._providers_file, mode="w") as file:
            await file.write(json.dumps(serializable_providers, indent=4))

    async def configure_provider_and_save_to_disk(
        self, llm_provider: CyrisLlmProvider, llm_provider_config: LlmProviderConfig
    ) -> None:
        self.configure_provider(
            llm_provider=llm_provider, llm_provider_config=llm_provider_config
        )
        await self._save_providers_to_disk()

    def configure_provider(
        self, llm_provider: CyrisLlmProvider, llm_provider_config: LlmProviderConfig
    ) -> None:
        self.providers[llm_provider].config = llm_provider_config
        provider_environment_variable_name = self.providers[
            llm_provider
        ].metadata.environment_variable_name
        os.environ[provider_environment_variable_name] = (
            llm_provider_config.environment_variable_value
        )

    def is_provider_configured(self, llm_provider: CyrisLlmProvider) -> bool:
        return self.providers[llm_provider].config is not None

    def get_provider_config_else_raise(
        self, llm_provider: CyrisLlmProvider
    ) -> LlmProviderConfig:
        config = self.providers[llm_provider].config
        if config:
            return config
        raise KeyError(f"LLM Provider {llm_provider=} is not configured.")

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
        model_metadata_by_model_name = (
            LlmProviderManager.get_model_metadata_by_model_name()
        )
        # TODO refactor to avoid assertions
        for model_name, model_metadata in model_metadata_by_model_name.items():
            assert isinstance(model_name, str)
            assert isinstance(model_metadata, dict)
            if model_metadata.get("mode") in ("chat", "completion"):
                available_models[
                    model_metadata.get("litellm_provider") or "misc"
                ].append(model_name)
        return available_models
