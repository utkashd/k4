this project has made me despise langchain

required env vars:

```bash
export GPT_HOME_HA_BASE_URL="https://homeassistant.local:8123"
export GPT_HOME_HA_TOKEN="long-lived api token here"
export GPT_HOME_OPENAI_API_KEY="openai api key here"
```

optional env vars:

```bash
export GPT_HOME_HA_IGNORE_SSL="1" # we only check for truthy values
```

<!-- install my project in editable mode w dev dependencies, so changes are live -->

python -m pip install -e ".[dev]"

<!-- to do: force use of vscode and ruff formatter -->
<!-- to do: gpg key or whatever to verify on GitHub -->
