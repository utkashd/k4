# Backend unit testing

If you create or make a change to a python file in the `backend/tests`
directory, pre-commit will run the test [when you try to commit the change].

If you need to skip this for some reason: `git commit --no-verify ...`

## Setup

This assumes you have installed `uv`:
<https://docs.astral.sh/uv/getting-started/installation/>

```zsh
cd ${K4_REPO_ROOT}/backend
uv sync
. .venv/bin/activate
pytest # run all tests
pytest tests/packages/api/src/api/test_extension_management.py # run specific test
```
