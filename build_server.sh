#!/bin/bash
set -euo pipefail # https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425

cd backend

docker build \
    --build-arg GPT_HOME_HA_IGNORE_SSL=$GPT_HOME_HA_IGNORE_SSL \
    --build-arg GPT_HOME_HA_TOKEN=$GPT_HOME_HA_TOKEN \
    --build-arg GPT_HOME_HUMAN_NAME=$GPT_HOME_HUMAN_NAME \
    --build-arg GPT_HOME_AI_NAME=$GPT_HOME_AI_NAME \
    --build-arg GPT_HOME_HA_BASE_URL=$GPT_HOME_HA_BASE_URL \
    --build-arg GPT_HOME_OPENAI_API_KEY=$GPT_HOME_OPENAI_API_KEY \
    --label gpt_home_backend_server \
    -t gpt_home_backend_server -f Dockerfile.server .

docker image prune --force --filter='label=gpt_home_backend_server' # save disk space

cd ../

# and then run with
# docker run -p 8000:8000 gpt_home_backend_server
