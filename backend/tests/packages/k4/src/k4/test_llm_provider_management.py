from k4.llm_provider_management import (
    LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT,
    K4LlmProvider,
)
from litellm import models_by_provider


def test_K4LlmProvider() -> None:
    for llm_provider in K4LlmProvider:
        assert llm_provider.value in models_by_provider


def test_llm_provider_info_dict_has_entry_for_each_K4LlmProvider() -> None:
    for llm_provider in K4LlmProvider:
        assert llm_provider in LLM_PROVIDER_INFO_BY_LLM_PROVIDER_DEFAULT
