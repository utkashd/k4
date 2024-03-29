from enum import StrEnum


# TODO: see if openai's library has this already; use that instead
# TODO improve descriptions of all models
class OpenAIModel(StrEnum):
    GPT_4 = "gpt-4"
    GPT_4_0613 = "gpt-4-0613"
    "Supports function calling"
    GPT_4_1106_PREVIEW = "gpt-4-1106-preview"
    "Supports function calling"
    GPT_4_32K = "gpt-4-32k"
    GPT_4_32K_0613 = "gpt-4-32k-0613"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_3_5_TURBO_0613 = "gpt-3.5-turbo-0613"
    "Supports function calling"
    GPT_3_5_TURBO_1106 = "gpt-3.5-turbo-1106"
    "Suggested in https://python.langchain.com/docs/modules/agents/agent_types/openai_tools"
    GPT_3_5_TURBO_16k = "gpt-3.5-turbo-16k"
    GPT_3_5_TURBO_16k_0613 = "gpt-3.5-turbo-16k-0613"
