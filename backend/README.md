# todo

build with

```zsh
docker build --rm -t backend:latest .
```

## developing

VSCode is strongly recommended

Requires docker desktop

set environment variables

install `uv`

```zsh
cd backend
uv sync
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
ipython -i <file path here>

...

In [1]: import asyncio
In [2]: asyncio.run(<async function here>)
```

### Using pre-commit

```bash
cd backend
. .venv/bin/activate
pre-commit run mypy
```

or replace `mypy` with a hook id from `.pre-commit-config.yaml`

```bash
pre-commit run --all-files
```
