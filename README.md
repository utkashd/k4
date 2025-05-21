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
