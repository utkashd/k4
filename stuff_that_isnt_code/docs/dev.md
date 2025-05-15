# Useful commands

```zsh
cd ${K4_REPO_ROOT}
docker compose logs backend
docker compose logs -f backend # live logs
```

```zsh
cd ${K4_REPO_ROOT}
docker compose exec -it backend bash
docker compose exec -it postgres bash
```

```zsh
cd ${K4_REPO_ROOT}
docker compose ps
```
