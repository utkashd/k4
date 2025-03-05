import json
import os
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from litellm import get_model_cost_map, model_cost_map_url  # type: ignore[attr-defined]
from pydantic import BaseModel
from utils import time_expiring_lru_cache


@dataclass
class LlmProviderConfig:
    default_model: str


@dataclass
class OpenAiProviderConfig(LlmProviderConfig):
    openai_api_key: str


@dataclass
class AnthropicProviderConfig(LlmProviderConfig):
    anthropic_api_key: str


@dataclass
class OllamaProviderConfig(LlmProviderConfig):
    ollama_api_host: str


class CyrisLlmProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class CyrisLlmProvidersConfig(BaseModel):
    preferred_provider: CyrisLlmProvider
    openai: OpenAiProviderConfig | None = None
    anthropic: AnthropicProviderConfig | None = None
    ollama: OllamaProviderConfig | None = None

    def get_llm_provider_config(
        self, llm_provider: CyrisLlmProvider
    ) -> LlmProviderConfig | None:
        config_or_none = self.__getattribute__(llm_provider.value)
        if not isinstance(config_or_none, LlmProviderConfig | None):
            raise KeyError(
                f"Unexpected input to this convenience function: {llm_provider=}"
            )
        return config_or_none


class LlmProviderManager:
    def __init__(self) -> None:
        providers_directory = Path.home().joinpath(".cyris/providers")
        providers_directory.mkdir(exist_ok=True, parents=True)

        self.providers_file_path = providers_directory.joinpath("llm_providers.json")
        if self.providers_file_path.exists():
            with open(self.providers_file_path, mode="r") as providers_file:
                self.providers = CyrisLlmProvidersConfig.model_validate_json(
                    json.load(providers_file)
                )
        else:
            self.providers = CyrisLlmProvidersConfig(
                preferred_provider=CyrisLlmProvider.OPENAI
            )

    def save_providers_to_file(self) -> None:
        with open(self.providers_file_path, mode="w") as providers_file:
            providers_file.write(self.providers.model_dump_json())

    def add_or_update_openai_provider(
        self, openai_provider_config: OpenAiProviderConfig
    ) -> None:
        self.providers.openai = openai_provider_config
        os.environ["OPENAI_API_KEY"] = openai_provider_config.openai_api_key
        self.save_providers_to_file()

    def add_or_update_anthropic_provider(
        self, anthropic_provider_config: AnthropicProviderConfig
    ) -> None:
        self.providers.anthropic = anthropic_provider_config
        os.environ["ANTHROPIC_API_KEY"] = anthropic_provider_config.anthropic_api_key
        self.save_providers_to_file()

    def add_or_update_ollama_provider(
        self, anthropic_provider_config: AnthropicProviderConfig
    ) -> None:
        self.providers.anthropic = anthropic_provider_config
        self.save_providers_to_file()

    def add_or_update_provider(
        self,
        llm_provider_name: CyrisLlmProvider,
        llm_provider_config: LlmProviderConfig,
    ) -> None:
        match llm_provider_name:
            case CyrisLlmProvider.OPENAI:
                assert isinstance(llm_provider_config, OpenAiProviderConfig)
                self.add_or_update_openai_provider(llm_provider_config)
            case CyrisLlmProvider.ANTHROPIC:
                assert isinstance(llm_provider_config, AnthropicProviderConfig)
                self.add_or_update_anthropic_provider(llm_provider_config)
            case CyrisLlmProvider.OLLAMA:
                assert isinstance(llm_provider_config, OllamaProviderConfig)
                self.providers.ollama = llm_provider_config
            case _:
                raise NotImplementedError(
                    f"Was provided a {llm_provider_config=} for {llm_provider_name=}, but adding that provider is unexpectedly not implemented."
                )

        self.providers.preferred_provider = llm_provider_name

    @lru_cache(maxsize=5)
    def is_provider_configured(self, llm_provider: CyrisLlmProvider) -> bool:
        return self.providers.get_llm_provider_config(llm_provider) is not None

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
