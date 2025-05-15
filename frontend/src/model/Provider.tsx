export enum K4LlmProvider {
    OPENAI = "openai",
    ANTHROPIC = "anthropic",
    OLLAMA = "ollama",
    OPENROUTER = "openrouter",
    HUGGINGFACE = "huggingface",
    GEMINI = "gemini",
}

type LlmProviderMetadata = {
    environment_variable_name: string;
};

type LlmProviderConfig = {
    environment_variable_value: string;
};

export type LlmProviderInfo = {
    llm_provider_name: K4LlmProvider;
    metadata: LlmProviderMetadata;
    config: LlmProviderConfig | null;
};
