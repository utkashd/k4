#!/bin/bash
set -euo pipefail # https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425

cd backend

docker build \
    --label cyris_backend_server_proxy \
    -t cyris_backend_server_proxy -f Dockerfile.server_proxy .

docker image prune --force --filter='label=cyris_backend_server_proxy' # save disk space

cd ../

# and then run with
# docker run -p 8001:8001 cyris_backend_server_proxy
