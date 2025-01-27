import os
from pathlib import Path


def get_repo_root_directory() -> Path:
    def does_string_end_with_suffix(string: str, suffix: str) -> bool:
        return string[len(string) - len(suffix) :] == suffix

    this_files_full_path = os.path.realpath(__file__)
    this_files_expected_path_relative_to_repo_root = (
        "./backend/packages/utils/src/utils/file_io.py"
    )
    if not does_string_end_with_suffix(
        this_files_full_path, this_files_expected_path_relative_to_repo_root[1:]
    ):
        raise Exception(
            "utils/file_io.py needs to be updated, as its location has changed"
        )

    current_dir_path = Path(os.path.realpath(__file__))
    for i in range(this_files_expected_path_relative_to_repo_root.count("/")):
        current_dir_path = current_dir_path.parent

    return current_dir_path
