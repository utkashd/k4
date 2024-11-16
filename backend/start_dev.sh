#!/bin/bash
set -euo pipefail # What this does: https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
END_COLOR='\033[0m' # No Color

# source /usr/local/bin/virtualenvwrapper.sh
# set +u # the "workon" command does a lot and we don't need to see it (+x) and uses some unbound variables (+u)
# echo "Activating the Python virtual environment cyris_backend"
# workon cyris_backend # activate the python environment. TODO set it up if doesn't exist
# set -u

printf "1.\tEnsuring Docker Desktop (/Applications/Docker.app) is running...\n"
if (! docker stats --no-stream > /dev/null 2>&1 ); then # if docker is not running
    printf "\t${YELLOW}Docker Desktop not running. Starting it now.${END_COLOR}\n"
    printf "\t${YELLOW}If a Docker Desktop window opens, you can close it.${END_COLOR}\n"
    sleep 3
    open /Applications/Docker.app
    while (! docker stats --no-stream > /dev/null 2>&1 ); do # while docker isn't yet running
        printf "\tWaiting for Docker Desktop to start...\n"
        sleep 3
    done
fi

printf "\t${GREEN}Docker Desktop is running.${END_COLOR}\n"


printf "2.\tEnsuring the postgres container is running...\n"
if [[ ! $( docker image ls postgres | grep postgres ) ]] ; then
    printf "\t${YELLOW}No postgres docker image found. Pulling the image and starting a container now.${END_COLOR}\n"
    set -x
    docker pull postgres:latest # TODO pin the postgres container version?
    docker run --name cyris-dev-postgres -e POSTGRES_PASSWORD=postgres -v postgresql-data:/var/lib/postgresql/data -p 5432:5432 -d postgres
    { set +x; } 2>/dev/null # normally `set +x` is printed. this is `set +x` but doesn't get printed
    # TODO create the volume if it doesn't already exist
elif [[ ! $( docker container ls -al | grep cyris-dev-postgres ) ]] ; then
    printf "\t${YELLOW}No postgres container found. Creating a container and starting it now.${END_COLOR}\n"
    set -x
    docker run --name cyris-dev-postgres -e POSTGRES_PASSWORD=postgres -e PAGER="less -S" -v postgresql-data:/var/lib/postgresql/data -p 5432:5432 -d postgres
    { set +x; } 2>/dev/null # normally `set +x` is printed. this is `set +x` but doesn't get printed
elif [[ ! $( docker ps -q -f name=cyris-dev-postgres ) ]] ; then
    printf "\t${YELLOW}postgres docker container found, but the container is not running. Starting it now.${END_COLOR}\n"
    set -x
    docker container start cyris-dev-postgres > /dev/null 2>&1 # TODO loop until the container is ready? 
    { set +x; } 2>/dev/null # normally `set +x` is printed. this is `set +x` but doesn't get printed
fi

printf "\t${GREEN}postgres docker container is running.${END_COLOR}\n"


printf "\n${GREEN}All set! Ready to develop 😎${END_COLOR}\n"
