# K4

A ChatGPT-style interface built for extendability.

## Setup

For now, setup is extremely unpolished (as development is ongoing and this isn't
a priority yet). But if you insist...this might work:

```zsh
git clone git@github.com:utkashd/k4.git
cd k4
echo "K4_BACKEND_SECRET_KEY=$(openssl rand -hex 32)" > .env
K4_ENVIRONMENT=development docker compose --project-directory . up --build -d
```

Then navigate to localhost:5173. The server will be localhost:8000

## smake

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
