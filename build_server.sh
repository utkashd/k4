#!/bin/bash
set -euo pipefail # https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425

cd backend

docker build \
    --build-arg CYRIS_HA_IGNORE_SSL=$CYRIS_HA_IGNORE_SSL \
    --build-arg CYRIS_HA_TOKEN=$CYRIS_HA_TOKEN \
    --build-arg CYRIS_HUMAN_NAME=$CYRIS_HUMAN_NAME \
    --build-arg CYRIS_AI_NAME=$CYRIS_AI_NAME \
    --build-arg CYRIS_HA_BASE_URL=$CYRIS_HA_BASE_URL \
    --build-arg CYRIS_OPENAI_API_KEY=$CYRIS_OPENAI_API_KEY \
    --label cyris_backend_server \
    -t cyris_backend_server -f Dockerfile.server .

docker image prune --force --filter='label=cyris_backend_server' # save disk space

cd ../

# and then run with
# docker run -p 8000:8000 cyris_backend_server
