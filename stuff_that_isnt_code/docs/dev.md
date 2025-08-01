# Dev setup

1. download & install docker desktop
2. install/update uv `uv self update`

## Useful commands

Inspect container logs

```zsh
cd ${K4_REPO_ROOT}
docker compose logs backend
docker compose logs -f backend # live logs
```

Get a shell in a container

```zsh
cd ${K4_REPO_ROOT}
docker compose exec -it backend bash
docker compose exec -it postgres bash
```

List docker processes

```zsh
cd ${K4_REPO_ROOT}
docker compose ps
```

### smake

smake is this project's development CLI tool. It provides convenient shortcuts
for common development tasks to make working on the project faster and easier.

To see what `smake` can do:

```zsh
./smake help
```

Key utilities include:

- start or stop the full K4 stack using docker compose
- launch K4’s frontend and backend services directly on the host machine (and
  postgres via docker compose)
- open a shell inside the Postgres container

If you'd like to make `smake` easier to use, you can add a couple of lines to
your `.zshrc`:

```zsh
export K4_REPO_ROOT="<path to k4 directory here>"
alias smake="${K4_REPO_ROOT}/smake"
```

This lets you run commands like `smake dev` instead of `./smake dev`.

### "Why not a Makefile?"

I honestly can't remember. I believe I started with a Makefile and ran into some
limitations.
