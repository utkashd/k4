import os
from pathlib import Path


def get_gpt_home_root_directory() -> Path:
    gpt_home_directory = Path(os.path.expanduser("~/.gpt_home/"))

    if not gpt_home_directory.exists():
        os.mkdir(gpt_home_directory)

    return gpt_home_directory


def get_the_users_directory() -> Path:
    # TODO rename this function so it's less confusing
    gpt_home_directory = get_gpt_home_root_directory()

    users_directory = Path(os.path.join(gpt_home_directory, "users/"))

    if not users_directory.exists():
        os.mkdir(users_directory)

    return users_directory


def get_a_users_directory(user_id: str) -> Path:
    # TODO rename this function so it's less confusing
    users_directory = get_the_users_directory()

    users_gpt_home_directory = Path(os.path.join(users_directory, user_id))

    if not users_gpt_home_directory.exists():
        os.mkdir(users_gpt_home_directory)

    return users_gpt_home_directory
