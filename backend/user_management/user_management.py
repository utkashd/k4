import logging
import warnings
import aiomysql  # type: ignore[import-untyped]
from aiomysql.pool import Pool  # type: ignore[import-untyped]

# from backend_commons.messages import Message
# from gpt_home.gpt_home import GptHomeDebugOptions
# from gpt_home.gpt_home_human import GptHomeHuman
from gpt_home.utils.utils import AsyncObject
from rich.logging import RichHandler

# from gpt_home.utils.file_io import get_gpt_home_root_directory
# import os
# from pathlib import Path
# from gpt_home import GptHome
from pydantic import BaseModel  # , RootModel
from typing import cast

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class RegisteredUser(BaseModel):
    """
    This holds all information necessary to recreate an instance of GptHome. IOW, we
    should be able to serialize a user with only this information (GptHome handles
    saving the factoids and chat history data, etc.)
    """

    user_email: str
    user_password: str
    human_name: str
    ai_name: str


# class GptHomeUsersAttrs(RootModel):  # type: ignore[type-arg]
#     root: dict[str, RegisteredUser]


# class ChatPreview(BaseModel):
#     pass


# class GptHomeUser:
#     def __init__(
#         self,
#         ai_name: str,
#         human_name: str,
#         user_email: str,
#         user_password: str,
#     ):
#         self.user_attributes = RegisteredUser(
#             user_email=user_email,
#             user_password=user_password,
#             human_name=human_name,
#             ai_name=ai_name,
#         )
#         self.gpt_home: GptHome | None = None

#     # def start_gpt_home(self) -> None:
#     #     """
#     #     This is an expensive function. It can cost a few minutes and a chunk of RAM.
#     #     TODO reuse devices across instances of GptHome to save (a ton) on RAM
#     #     """
#     #     if not self.gpt_home:
#     #         self.gpt_home = GptHome(
#     #             gpt_home_human=GptHomeHuman(
#     #                 ai_name=self.user_attributes.ai_name,
#     #                 user_id=self.user_attributes.user_id,
#     #                 human_name=self.user_attributes.human_name,
#     #             ),
#     #             debug_options=GptHomeDebugOptions(log_level="warn", is_dry_run=False),
#     #             ignore_home_assistant_ssl=True,
#     #         )

#     # def stop_gpt_home(self) -> None:
#     #     if self.gpt_home:
#     #         self.gpt_home.stop_chatting()
#     #         # save ram, but the next time the user logs in, the user will have to wait?
#     #         # idk if this is a good decision.
#     #         # **Update** Which is why I'm commenting it out! lol
#     #         # self.gpt_home = None

#     # def ask_gpt_home(self, human_input: str) -> list[Message]:
#     #     if self.gpt_home:
#     #         return self.gpt_home.ask_gpt_home(human_input)
#     #     return []

#     def get_user_attributes(self) -> RegisteredUser:
#         return self.user_attributes


class UsersManagerAsync(AsyncObject):
    """
    This class is intended to be instantiated like so:

    ```
    users_manager = await UsersManagerAsync()
    ```

    This lets us start the asynchronous DB connection pool upon instantiation.
    """

    async def __init__(self):
        log.info("Starting the users DB connection pool")
        # TODO error handling if connection fails
        self.mysql_connection_pool = await aiomysql.create_pool(
            host="localhost",
            port=3306,
            user="root",
            password="gpthome",
            db="mydb",
            minsize=1,
            maxsize=5,
        )
        self.mysql_connection_pool = cast(Pool, self.mysql_connection_pool)
        if self.mysql_connection_pool._free:  # `.is_serving()` is not implemented
            log.info("Successfully started the users DB connection pool")

        log.info("Creating the users table if it doesn't already exist")
        # Suppress warnings only for aiomysql, all other modules can send warnings
        warnings.filterwarnings("ignore", module=r"aiomysql")
        async with self.mysql_connection_pool.acquire() as connection:
            connection = cast(aiomysql.connection.Connection, connection)
            async with connection.cursor() as cursor:
                cursor = cast(aiomysql.cursors.Cursor, cursor)
                await cursor.execute("""
                                     CREATE TABLE IF NOT EXISTS users (user_id INT
                                     AUTO_INCREMENT PRIMARY KEY, user_email VARCHAR(255)
                                     NOT NULL UNIQUE, user_password VARCHAR(255) NOT NULL,
                                     human_name VARCHAR(255) NOT NULL, ai_name VARCHAR(255))
                                     """)
                await connection.commit()
        # Enable warnings again
        warnings.filterwarnings("default", module=r"aiomysql")
        log.info("Finished ensuring the users table is created")

    async def end(self):
        log.info("Closing the users DB connection pool")
        self.mysql_connection_pool.close()
        await self.mysql_connection_pool.wait_closed()

        # self.prepared_statements: dict[
        #     str, tuple[mysql.connector.cursor.MySQLCursorAbstract, str]
        # ] = {
        #     "insert a new user": (
        #         self.mysql_connection.cursor(prepared=True),
        #         "INSERT INTO users (user_email, user_password, human_name, ai_name) VALUES (%(user_email)s, %(user_password)s, %(human_name)s, %(ai_name)s)",
        #     )
        # }

    async def get_users_async(self) -> tuple:
        async with self.mysql_connection_pool.acquire() as connection:
            connection = cast(
                aiomysql.connection.Connection, connection
            )  # this is just so VSCode + mypy works nicely
            async with connection.cursor() as cursor:
                cursor = cast(aiomysql.cursors.Cursor, cursor)
                await cursor.execute("SELECT * FROM users LIMIT 5;")
                response = await cursor.fetchall()
                return response
        # self.general_mysql_cursor.execute("SELECT * FROM users LIMIT 5")
        # results = self.general_mysql_cursor.fetchall()
        # # for row in results:
        # #     print(row)

        # return [user.get_user_attributes() for _, user in self.users.items()]

    # def start_user(self, user: GptHomeUser) -> None:
    #     user.start_gpt_home()

    # def stop_user(self, user: GptHomeUser) -> None:
    #     user.stop_gpt_home()

    # def get_user(self, user_id: str) -> GptHomeUser | None:
    #     pass

    # async def create_user(
    #     self, user_email: str, user_password: str, human_name: str, ai_name: str
    # ) -> RegisteredUser:
    #     """
    #     Creates a user and saves the list of users to the filesystem.

    #     Returns
    #     -------
    #     str
    #         The new user's user_id
    #     """

    #     gpt_home_user = GptHomeUser(
    #         ai_name=ai_name,
    #         human_name=human_name,
    #         user_email=user_email,
    #         user_password=user_password,
    #     )
    #     # self.users[user_email] = gpt_home_user
    #     # self._save_users_to_filesystem()

    #     def _write_new_user_to_db(gpt_home_user_attributes: RegisteredUser):
    #         # TODO validate the inputs
    #         try:
    #             insert_user_cursor, insert_user_statement = self.prepared_statements[
    #                 "insert a new user"
    #             ]
    #             insert_user_cursor.execute(
    #                 insert_user_statement,
    #                 {
    #                     "user_email": gpt_home_user_attributes.user_email,
    #                     "user_password": gpt_home_user_attributes.user_password,
    #                     "ai_name": gpt_home_user_attributes.ai_name,
    #                     "human_name": gpt_home_user_attributes.human_name,
    #                 },
    #             )
    #             self.mysql_connection.commit()
    #         except mysql.connector.Error as err:
    #             self.mysql_connection.rollback()
    #             print(f"Something went wrong: {err}")
    #             if err.errno == mysql.connector.errorcode.ER_DUP_ENTRY:
    #                 raise Exception(
    #                     f"User with email {gpt_home_user.user_attributes.user_email} already exists"
    #                 )
    #             else:
    #                 raise Exception("An unexpected error occurred")

    #     _write_new_user_to_db(gpt_home_user.user_attributes)
    #     return gpt_home_user.get_user_attributes()

    def delete_user(self, user_id: str) -> None:
        pass
        # if self.users.get(user_id):
        #     self.stop_user(self.users[user_id])
        #     if self.users[user_id].gpt_home:
        #         # ensure we free up the memory. prob not necessary tbh
        #         self.users[user_id].gpt_home = None
        #     self.users.pop(user_id)
        #     self._save_users_to_filesystem()

    # def get_user_chat_previews(
    #     self, user_id: str, start: int, end: int
    # ) -> list[ChatPreview]:
    #     # if self.users.get(user_id):
    #     #     pass
    #     return []

    # def _save_users_to_filesystem(self) -> None:
    #     users_filename = self._get_users_filename()
    #     with open(users_filename, "w") as users_file:
    #         json.dump(
    #             {
    #                 user_id: gpt_home_user.get_user_attributes().model_dump()
    #                 for user_id, gpt_home_user in self.users.items()
    #             },
    #             users_file,
    #             indent=4,
    #         )

    # def _load_users_from_filesystem(self) -> dict[str, GptHomeUser]:
    #     users_filename = self._get_users_filename()
    #     if not os.path.exists(users_filename):
    #         return {}
    #     gpt_home_users_attrs: dict[str, GptHomeUserAttributes] = {}
    #     with open(users_filename, "r") as users_file:
    #         gpt_home_users_attrs = GptHomeUsersAttrs(json.load(users_file)).root

    #     users: dict[str, GptHomeUser] = {}
    #     for user_attributes in gpt_home_users_attrs.values():
    #         gpt_home_user = GptHomeUser(
    #             ai_name=user_attributes.ai_name,
    #             human_name=user_attributes.human_name,
    #             user_id=user_attributes.user_id,
    #         )
    #         users[user_attributes.user_id] = gpt_home_user

    #     return users

    # def _get_users_filename(self) -> Path:
    #     """
    #     File is not guaranteed to exist

    #     Returns
    #     -------
    #     Path
    #         The path to the file where user attributes are stored in json format
    #     """
    #     users_directory = self._get_users_directory_and_create_if_necessary()
    #     users_filename = os.path.join(users_directory, "users.json")
    #     return Path(users_filename)

    # def _get_users_directory_and_create_if_necessary(self) -> Path:
    #     gpt_home_directory = get_gpt_home_root_directory()
    #     users_directory = os.path.join(gpt_home_directory, "users")
    #     if not os.path.exists(users_directory):
    #         os.mkdir(users_directory)
    #     return Path(users_directory)
