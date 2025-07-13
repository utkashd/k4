import os
from functools import lru_cache
from pathlib import Path

from utils.environment import is_running_in_docker_container


@lru_cache(maxsize=1)
def get_repo_root_directory() -> Path:
    """
    Gets the root directory of this repository. Finds it by returning the directory
    where the `.k4_repo_root` file is
    """

    if is_running_in_docker_container():
        raise Exception("There is no repo root when you're running in the container")

    def does_directory_contain_repo_root_file(directory: Path) -> bool:
        if not directory.is_dir():
            raise Exception(f"{directory=} needs to be a directory")
        return directory.joinpath(".k4_repo_root").is_file()

    this_files_full_path = Path(os.path.realpath(__file__))
    current_directory = this_files_full_path.parent
    while not does_directory_contain_repo_root_file(current_directory):
        current_directory = current_directory.parent

    return current_directory


@lru_cache(maxsize=1)
def get_backend_root_directory() -> Path:
    """
    Gets the root directory of the backend. Finds it by returning the directory
    where the `.k4_backend_root` file is
    """

    if is_running_in_docker_container():
        # there is a directory, but it's not the same as developing locally
        raise Exception("There is no backend root when you're running in the container")

    def does_directory_contain_backend_root_file(directory: Path) -> bool:
        if not directory.is_dir():
            raise Exception(f"{directory=} needs to be a directory")
        return directory.joinpath(".k4_backend_root").is_file()

    this_files_full_path = Path(os.path.realpath(__file__))
    current_directory = this_files_full_path.parent
    while not does_directory_contain_backend_root_file(current_directory):
        current_directory = current_directory.parent

    return current_directory


@lru_cache(maxsize=1)
def get_k4_data_directory() -> Path:
    if is_running_in_docker_container():
        k4_data_directory = Path("/k4_data")
    else:
        k4_data_directory = Path.home().joinpath(".k4")
    k4_data_directory.mkdir(exist_ok=True)
    return k4_data_directory
