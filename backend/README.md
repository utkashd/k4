# todo

build with

```zsh
docker build --rm -t backend:latest .
```

## developing

VSCode is strongly recommended

Requires docker desktop

install `uv`

```zsh
cd backend
uv sync
```

install `npm`

```zsh
cd frontend
npm install
```

### development scripts

```zsh
./start_dev.sh
```

```zsh
./stop_dev.sh
```

### debugging

You should be able to put a `breakpoint()` call anywhere

If you want to debug just the contents of one file:

```zsh
cd backend
. .venv/bin/activate
python -i <file path here>

...

>> import asyncio
>> asyncio.run(<async function call here>)
```

### using pre-commit

```zsh
cd backend && \
    uv sync && \
    . .venv/bin/activate && \
    cd .. && \
    pre-commit install
pre-commit run --all-files
```

or specify a hook id from `.pre-commit-config.yaml`:

```zsh
pre-commit run --all-files mypy
```
