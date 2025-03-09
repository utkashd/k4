from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from litellm import get_model_cost_map, model_cost_map_url  # type: ignore[attr-defined]
from utils import time_expiring_lru_cache


class CyrisLlmProvider(Enum):
    # Important that the strings match the model names used by litellm: see litellm.models_by_provider
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


@dataclass
class LlmProviderMetadata:
    environment_variable_name: str


@dataclass
class LlmProviderConfig:
    environment_variable_value: str


@dataclass
class LlmProviderInfo:
    metadata: LlmProviderMetadata
    config: LlmProviderConfig | None


LLM_PROVIDER_INFO_BY_LLM_PROVIDER: dict[CyrisLlmProvider, LlmProviderInfo] = {
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
}


class LlmProviderManager:
    def __init__(self) -> None:
        providers_directory = Path.home().joinpath(".cyris/providers")
        providers_directory.mkdir(exist_ok=True, parents=True)

        self.providers = LLM_PROVIDER_INFO_BY_LLM_PROVIDER

    async def _save_providers_to_disk(self) -> None:
        pass

    async def configure_provider(
        self, llm_provider: CyrisLlmProvider, llm_provider_config: LlmProviderConfig
    ) -> None:
        self.providers[llm_provider].config = llm_provider_config
        await self._save_providers_to_disk()

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
