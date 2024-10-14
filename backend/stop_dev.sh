#!/bin/bash
set -euo pipefail # What this does: https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
END_COLOR='\033[0m' # No Color

echo "1. Stopping the mysql container."
set -x
docker container stop mysql-dev > /dev/null 2>&1
{ set +x; } 2>/dev/null # normally `set +x` is printed. this is `set +x` but doesn't get printed
printf "${GREEN}mysql container is stopped.${END_COLOR}"

printf "\n${GREEN}All set! Ready to chill 😎${END_COLOR}\n"

# set +x
# source /usr/local/bin/virtualenvwrapper.sh
# set -x
# deactivate
