```bash
# cd backend
mkvirtualenv -p python3.12 cyris_backend
python -m pip install poetry
poetry install
```

this project has made me despise langchain

required env vars:

```bash
export CYRIS_HA_BASE_URL="https://homeassistant.local:8123"
export CYRIS_HA_TOKEN="long-lived api token here"
export CYRIS_OPENAI_API_KEY="openai api key here"
```

to develop

```bash
mkvirtualenv -p python3.12 cyris
python -m pip install -e ".[dev]"
```

optional env vars:

```bash
export CYRIS_HA_IGNORE_SSL="1" # we only check for truthy values
```

<!-- install my project in editable mode w dev dependencies, so changes are live -->

python -m pip install -e ".[dev]"

<!-- to do: force use of vscode and ruff formatter -->
<!-- to do: gpg key or whatever to verify on GitHub -->
