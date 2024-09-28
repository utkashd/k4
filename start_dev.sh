#!/bin/bash
set -euo pipefail # What this does: https://gist.github.com/mohanpedala/1e2ff5661761d3abd0385e8223e16425

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
END_COLOR='\033[0m' # No Color

# source /usr/local/bin/virtualenvwrapper.sh
# set +u # the "workon" command does a lot and we don't need to see it (+x) and uses some unbound variables (+u)
# echo "Activating the Python virtual environment gpt_home_backend"
# workon gpt_home_backend # activate the python environment. TODO set it up if doesn't exist
# set -u

echo "1. Ensuring Docker Desktop (/Applications/Docker.app) is running..."
if (! docker stats --no-stream > /dev/null 2>&1 ); then # if docker is not running
    printf "${RED}Docker Desktop not running. Starting it now.${END_COLOR}\n"
    printf "${YELLOW}If a Docker Desktop window opens, you can close it.${END_COLOR}\n"
    sleep 3
    open /Applications/Docker.app
    while (! docker stats --no-stream > /dev/null 2>&1 ); do # while docker isn't yet running
        echo "Waiting for Docker Desktop to start..."
        sleep 1
    done
fi

printf "${GREEN}Docker Desktop is running.${END_COLOR}\n"


echo "2. Ensuring the mysql container is running..."
if [[ ! $( docker image ls mysql | grep mysql ) ]] ; then
    echo "No mysql docker image found. Pulling the image and starting a container now."
    set -x
    docker pull mysql:latest # TODO pin the mysql container version?
    docker run --name mysql-dev -e MYSQL_ROOT_PASSWORD=gpthome -e MYSQL_DATABASE=mydb -v mysql-data:/var/lib/mysql -p 3306:3306 -d mysql
    { set +x; } 2>/dev/null # normally `set +x` is printed. this is `set +x` but doesn't get printed
elif [[ ! $(docker ps -q -f name=mysql-dev ) ]] ; then
    echo "mysql docker image found, but the container is not running. Starting it now." 
    set -x
    docker container start mysql-dev > /dev/null 2>&1 # TODO loop until the container is ready? 
    { set +x; } 2>/dev/null # normally `set +x` is printed. this is `set +x` but doesn't get printed
fi

printf "${GREEN}mysql docker container is running.${END_COLOR}\n"


printf "\n${GREEN}All set! Ready to develop 😎${END_COLOR}\n"
