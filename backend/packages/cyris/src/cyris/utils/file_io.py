from functools import lru_cache
import os
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel


def get_cyris_root_directory() -> Path:
    cyris_directory = Path(os.path.expanduser("~/.cyris/"))

    if not cyris_directory.exists():
        os.mkdir(cyris_directory)

    return cyris_directory


def get_the_users_directory() -> Path:
    # TODO rename this function so it's less confusing
    cyris_directory = get_cyris_root_directory()

    users_directory = Path(os.path.join(cyris_directory, "users/"))

    if not users_directory.exists():
        os.mkdir(users_directory)

    return users_directory


def get_a_users_directory(user_id: str) -> Path:
    # TODO rename this function so it's less confusing
    users_directory = get_the_users_directory()

    users_cyris_directory = Path(os.path.join(users_directory, user_id))

    if not users_cyris_directory.exists():
        os.mkdir(users_cyris_directory)

    return users_cyris_directory


def get_a_users_chat_history_preview_directory(user_id: str) -> Path:
    users_directory = get_a_users_directory(user_id)

    users_chat_history_directory = Path(
        os.path.join(users_directory, "chat_history_preview/")
    )

    if not users_chat_history_directory.exists():
        os.mkdir(users_chat_history_directory)

    return users_chat_history_directory


def get_a_users_chat_history_directory(user_id: str) -> Path:
    users_directory = get_a_users_directory(user_id)

    users_chat_history_directory = Path(os.path.join(users_directory, "chat_history/"))

    if not users_chat_history_directory.exists():
        os.mkdir(users_chat_history_directory)

    return users_chat_history_directory


class ChatHistoryDirectories(BaseModel):
    chat_history_directory: Path
    chat_history_preview_directory: Path


@lru_cache(maxsize=30)
def _get_chat_history_directory_and_chat_history_preview_directory_for_timestamp_cached(
    user_id: str, year: str, month: str, day: str
) -> ChatHistoryDirectories:
    users_chat_history_directory = get_a_users_chat_history_directory(user_id)
    chat_history_for_that_day_directory = Path(
        os.path.join(users_chat_history_directory, f"{year}-{month}-{day}/")
    )
    if not chat_history_for_that_day_directory.exists():
        os.mkdir(chat_history_for_that_day_directory)

    users_chat_history_preview_directory = get_a_users_chat_history_preview_directory(
        user_id
    )
    chat_history_preview_for_that_day_directory = Path(
        os.path.join(users_chat_history_preview_directory, f"{year}-{month}-{day}/")
    )
    if not chat_history_preview_for_that_day_directory.exists():
        os.mkdir(chat_history_preview_for_that_day_directory)

    return ChatHistoryDirectories(
        chat_history_directory=chat_history_for_that_day_directory,
        chat_history_preview_directory=chat_history_preview_for_that_day_directory,
    )


def get_chat_history_directory_and_chat_history_preview_directory_for_timestamp(
    user_id: str, timestamp: float
) -> ChatHistoryDirectories:
    date_and_time = datetime.fromtimestamp(timestamp)
    year = str(date_and_time.year)
    month = (
        str(date_and_time.month)
        if date_and_time.month >= 10
        else f"0{date_and_time.month}"
    )
    day = str(date_and_time.day) if date_and_time.day >= 10 else f"0{date_and_time.day}"

    return _get_chat_history_directory_and_chat_history_preview_directory_for_timestamp_cached(
        user_id, year, month, day
    )
