import os
from pathlib import Path


def get_gpt_home_directory():
    gpt_home_directory = Path(os.path.expanduser("~/.gpt_home/"))

    if not gpt_home_directory.exists():
        os.mkdir(gpt_home_directory)

    return gpt_home_directory
