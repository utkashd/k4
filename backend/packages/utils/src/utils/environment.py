import os
from enum import Enum
from functools import cache


@cache
def is_running_in_docker_container() -> bool:
    return os.getenv("IN_CONTAINER") == "true"


class K4Environment(Enum):
    DEVELOPMENT = 1
    PRODUCTION = 2


@cache
def get_environment() -> K4Environment:
    if os.getenv("K4_ENVIRONMENT") == "development":
        return K4Environment.DEVELOPMENT
    return K4Environment.PRODUCTION


def is_development_environment() -> bool:
    return get_environment() == K4Environment.DEVELOPMENT


def is_production_environment() -> bool:
    return get_environment() == K4Environment.PRODUCTION
