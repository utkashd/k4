import logging
from backend_commons.messages import Message
from gpt_home.gpt_home import GptHomeDebugOptions
from gpt_home.gpt_home_human import GptHomeHuman
from rich.logging import RichHandler
from gpt_home.utils.file_io import get_gpt_home_root_directory
import os
from pathlib import Path
import json
import uuid
from gpt_home import GptHome
from pydantic import BaseModel, RootModel

FORMAT = "%(message)s"
logging.basicConfig(
    level="WARN", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class GptHomeUserAttributes(BaseModel):
    """
    This holds all information necessary to recreate an instance of GptHome. IOW, we
    should be able to serialize a user with only this information (GptHome handles
    saving the factoids and chat history data, etc.)
    """

    user_id: str
    human_name: str
    ai_name: str


class GptHomeUsersAttrs(RootModel):  # type: ignore[type-arg]
    root: dict[str, GptHomeUserAttributes]


class ChatPreview(BaseModel):
    pass


class GptHomeUser:
    def __init__(self, ai_name: str, human_name: str, user_id: str):
        self.user_attributes = GptHomeUserAttributes(
            user_id=user_id,
            human_name=human_name,
            ai_name=ai_name,
        )
        self.gpt_home: GptHome | None = None

    def start_gpt_home(self) -> None:
        """
        This is an expensive function. It can cost a few minutes and a chunk of RAM.
        TODO reuse devices across instances of GptHome to save (a ton) on RAM
        """
        if not self.gpt_home:
            self.gpt_home = GptHome(
                gpt_home_human=GptHomeHuman(
                    ai_name=self.user_attributes.ai_name,
                    user_id=self.user_attributes.user_id,
                    human_name=self.user_attributes.human_name,
                ),
                debug_options=GptHomeDebugOptions(log_level="warn", is_dry_run=False),
                ignore_home_assistant_ssl=True,
            )

    def stop_gpt_home(self) -> None:
        if self.gpt_home:
            self.gpt_home.stop_chatting()
            # save ram, but the next time the user logs in, the user will have to wait?
            # idk if this is a good decision.
            # **Update** Which is why I'm commenting it out! lol
            # self.gpt_home = None

    def ask_gpt_home(self, human_input: str) -> list[Message]:
        if self.gpt_home:
            return self.gpt_home.ask_gpt_home(human_input)
        return []

    def get_user_attributes(self) -> GptHomeUserAttributes:
        return self.user_attributes


class UsersManager:
    def __init__(self) -> None:
        self.users: dict[str, GptHomeUser] = self._load_users_from_filesystem()

    def get_users(self) -> list[GptHomeUserAttributes]:
        return [user.get_user_attributes() for _, user in self.users.items()]

    def start_user(self, user: GptHomeUser) -> None:
        user.start_gpt_home()

    def stop_user(self, user: GptHomeUser) -> None:
        user.stop_gpt_home()

    def get_user(self, user_id: str) -> GptHomeUser | None:
        return self.users.get(user_id)

    def create_user(self, ai_name: str, human_name: str) -> GptHomeUserAttributes:
        """
        Creates a user and saves the list of users to the filesystem.

        Returns
        -------
        str
            The new user's user_id
        """
        user_id = str(uuid.uuid4())
        gpt_home_user = GptHomeUser(
            ai_name=ai_name,
            human_name=human_name,
            user_id=user_id,
        )
        self.users[user_id] = gpt_home_user
        self._save_users_to_filesystem()
        return gpt_home_user.get_user_attributes()

    def delete_user(self, user_id: str) -> None:
        if self.users.get(user_id):
            self.stop_user(self.users[user_id])
            if self.users[user_id].gpt_home:
                # ensure we free up the memory. prob not necessary tbh
                self.users[user_id].gpt_home = None
            self.users.pop(user_id)
            self._save_users_to_filesystem()

    def get_user_chat_previews(
        self, user_id: str, start: int, end: int
    ) -> list[ChatPreview]:
        if self.users.get(user_id):
            pass
        return []

    def _save_users_to_filesystem(self) -> None:
        users_filename = self._get_users_filename()
        with open(users_filename, "w") as users_file:
            json.dump(
                {
                    user_id: gpt_home_user.get_user_attributes().model_dump()
                    for user_id, gpt_home_user in self.users.items()
                },
                users_file,
                indent=4,
            )

    def _load_users_from_filesystem(self) -> dict[str, GptHomeUser]:
        users_filename = self._get_users_filename()
        if not os.path.exists(users_filename):
            return {}
        gpt_home_users_attrs: dict[str, GptHomeUserAttributes] = {}
        with open(users_filename, "r") as users_file:
            gpt_home_users_attrs = GptHomeUsersAttrs(json.load(users_file)).root

        users: dict[str, GptHomeUser] = {}
        for user_attributes in gpt_home_users_attrs.values():
            gpt_home_user = GptHomeUser(
                ai_name=user_attributes.ai_name,
                human_name=user_attributes.human_name,
                user_id=user_attributes.user_id,
            )
            users[user_attributes.user_id] = gpt_home_user

        return users

    def _get_users_filename(self) -> Path:
        """
        File is not guaranteed to exist

        Returns
        -------
        Path
            The path to the file where user attributes are stored in json format
        """
        users_directory = self._get_users_directory_and_create_if_necessary()
        users_filename = os.path.join(users_directory, "users.json")
        return Path(users_filename)

    def _get_users_directory_and_create_if_necessary(self) -> Path:
        gpt_home_directory = get_gpt_home_root_directory()
        users_directory = os.path.join(gpt_home_directory, "users")
        if not os.path.exists(users_directory):
            os.mkdir(users_directory)
        return Path(users_directory)
