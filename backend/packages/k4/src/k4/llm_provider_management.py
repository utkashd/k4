import os
from collections import defaultdict
from enum import StrEnum

from litellm import get_model_cost_map  # type: ignore[attr-defined]
from litellm import model_cost_map_url
from pydantic import BaseModel, SecretStr
from utils import TypedDiskCache, time_expiring_lru_cache
from utils.file_io import get_k4_data_directory


class LlmProviderMetadata(BaseModel):
    environment_variable_name: str


class LlmProviderConfig(BaseModel):
    environment_variable_value: SecretStr


class K4LlmProvider(StrEnum):
    # Important that the strings match the model names used by litellm: see litellm.models_by_provider
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"
    GEMINI = "gemini"


class LlmProviderInfo(BaseModel):
    llm_provider_name: K4LlmProvider
    metadata: LlmProviderMetadata
    config: LlmProviderConfig | None


LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT: dict[K4LlmProvider, LlmProviderInfo] = {
    K4LlmProvider.OPENAI: LlmProviderInfo(
        llm_provider_name=K4LlmProvider.OPENAI,
        metadata=LlmProviderMetadata(environment_variable_name="OPENAI_API_KEY"),
        config=None,
    ),
    K4LlmProvider.ANTHROPIC: LlmProviderInfo(
        llm_provider_name=K4LlmProvider.ANTHROPIC,
        metadata=LlmProviderMetadata(environment_variable_name="ANTHROPIC_API_KEY"),
        config=None,
    ),
    K4LlmProvider.OLLAMA: LlmProviderInfo(
        llm_provider_name=K4LlmProvider.OLLAMA,
        metadata=LlmProviderMetadata(environment_variable_name="OLLAMA_BASE_URL"),
        config=None,
    ),
    K4LlmProvider.OPENROUTER: LlmProviderInfo(
        llm_provider_name=K4LlmProvider.OPENROUTER,
        metadata=LlmProviderMetadata(environment_variable_name="OPENROUTER_API_KEY"),
        config=None,
    ),
    K4LlmProvider.HUGGINGFACE: LlmProviderInfo(
        llm_provider_name=K4LlmProvider.HUGGINGFACE,
        metadata=LlmProviderMetadata(environment_variable_name="HUGGINGFACE_API_KEY"),
        config=None,
    ),
    K4LlmProvider.GEMINI: LlmProviderInfo(
        llm_provider_name=K4LlmProvider.GEMINI,
        metadata=LlmProviderMetadata(environment_variable_name="GEMINI_API_KEY"),
        config=None,
    ),
}


class LlmProviderManager:
    def __init__(self) -> None:
        self.providers_cache = TypedDiskCache[K4LlmProvider, LlmProviderInfo](
            directory=get_k4_data_directory().joinpath("providers")
        )

        for llm_provider in LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT.keys():
            if llm_provider not in self.providers_cache:
                self.providers_cache[llm_provider] = (
                    LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT[llm_provider]
                )

    def set_provider_config(
        self, llm_provider: K4LlmProvider, config: LlmProviderConfig | None
    ) -> None:
        LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT[llm_provider].config = config
        self.providers_cache[llm_provider] = LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT[
            llm_provider
        ]

        provider_environment_variable_name = LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT[
            llm_provider
        ].metadata.environment_variable_name
        if config is not None:
            os.environ[provider_environment_variable_name] = (
                config.environment_variable_value.get_secret_value()
            )
        else:
            os.environ[provider_environment_variable_name] = ""

    def is_provider_configured(self, llm_provider: K4LlmProvider) -> bool:
        return (
            self.providers_cache.get(llm_provider) is not None
            and self.providers_cache[llm_provider].config is not None
        )

    def get_provider_config_else_raise(
        self, llm_provider: K4LlmProvider
    ) -> LlmProviderConfig:
        config = self.providers_cache[llm_provider].config
        if config:
            return config
        raise KeyError(f"LLM Provider {llm_provider=} is not configured.")

    @staticmethod
    @time_expiring_lru_cache(max_age_seconds=60 * 10, max_size=1)
    def get_model_metadata_by_model_name() -> dict:  # type: ignore[type-arg]
        # we don't have a guarantee for the litellm json's structure, iirc. though I may
        # have added it upstream in a test file lol
        model_metadata_by_model_name = get_model_cost_map(url=model_cost_map_url)
        assert isinstance(model_metadata_by_model_name, dict)
        return model_metadata_by_model_name

    def get_available_models(self) -> dict[str, list[str]]:
        # TODO invalidate the cache when the providers list is updated. This is fine for
        # now though
        available_models: dict[str, list[str]] = defaultdict(list)
        model_metadata_by_model_name = (
            LlmProviderManager.get_model_metadata_by_model_name()
        )
        for model_name, model_metadata in model_metadata_by_model_name.items():
            assert isinstance(model_name, str)
            assert isinstance(model_metadata, dict)
            if model_metadata.get(
                "litellm_provider"
            ) in K4LlmProvider and self.is_provider_configured(
                K4LlmProvider(model_metadata["litellm_provider"])
            ):
                if model_metadata.get("mode") in ("chat", "completion"):
                    available_models[
                        model_metadata.get("litellm_provider") or "misc"
                    ].append(model_name)
        return available_models
