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
