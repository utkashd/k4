import logging
import aiomysql  # type: ignore[import-untyped]

# from backend_commons.messages import Message
# from gpt_home.gpt_home import GptHomeDebugOptions
# from gpt_home.gpt_home_human import GptHomeHuman
from fastapi import HTTPException
from gpt_home.utils.utils import AsyncObject
from rich.logging import RichHandler

# from gpt_home.utils.file_io import get_gpt_home_root_directory
# import os
# from pathlib import Path
# from gpt_home import GptHome
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, SecretStr  # , RootModel
from typing import cast

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class RegisteredUser(BaseModel):
    user_id: int
    user_email: EmailStr
    hashed_user_password: SecretStr
    human_name: str = Field(min_length=1)
    ai_name: str = Field(min_length=1)
    is_user_email_verified: bool  # `0 | 1` works natively https://docs.pydantic.dev/2.9/api/standard_library_types/#booleans


class RegistrationAttempt(BaseModel):
    """
    Holds attributes corresponding to a new user attempting to register.
    """

    desired_user_email: str
    hashed_user_password: SecretStr
    desired_human_name: str
    desired_ai_name: str


SECRET_KEY = "18e8e912cce442d5fe6af43a003dedd7cedd7248efc16ac926f21f8f940398a8"  # Generated with `openssl rand -hex 32`
ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30


class Token(BaseModel):
    jwt: str
    token_type: str


class TokenData(BaseModel):
    user_email: str | None = None


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
        self.mysql_connection_pool = cast(aiomysql.Pool, self.mysql_connection_pool)
        if self.mysql_connection_pool._free:  # `.is_serving()` is not implemented
            log.info("Successfully started the users DB connection pool")

        self._ensure_users_table_is_created_in_db()

        self.pwd_context = CryptContext(schemes=["bcrypt"])
        self.oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    async def _ensure_users_table_is_created_in_db(self):
        log.info(
            """Creating the users table if it doesn't already exist. You may see a
            warning from aiomysql that the table already exists, this is expected and
            harmless."""
        )
        async with cast(
            aiomysql.Connection, self.mysql_connection_pool.acquire()
        ) as connection:
            async with cast(aiomysql.cursors.Cursor, connection.cursor()) as cursor:
                # If you're changing the table, you'll need to drop the existing table
                # on your local machine first. Something like:
                # > docker exec -it mysql-dev bash
                # > > mysql -u root -p # the password is in <repo root>/start_dev.sh
                # > > > drop table mydb.users;
                # `exit` a couple times to return to your terminal
                # TODO should have a script or something for modifying tables elegantly
                await cursor.execute("""
                                     CREATE TABLE IF NOT EXISTS users 
                                     (
                                     user_id INT AUTO_INCREMENT PRIMARY KEY,
                                     user_email VARCHAR(255) NOT NULL UNIQUE,
                                     hashed_user_password VARCHAR(255) NOT NULL,
                                     human_name VARCHAR(255) NOT NULL,
                                     ai_name VARCHAR(255),
                                     is_user_email_verified BIT NOT NULL,
                                     INDEX idx_user_email (user_email)
                                     )
                                     """)
                await connection.commit()
        log.info("Finished ensuring the users table is created")

    async def end(self):
        log.info("Closing the users DB connection pool")
        self.mysql_connection_pool.close()
        await self.mysql_connection_pool.wait_closed()

    async def get_five_users_async(self) -> list[RegisteredUser]:
        async with cast(
            aiomysql.Connection, self.mysql_connection_pool.acquire()
        ) as connection:
            async with cast(
                aiomysql.DictCursor, connection.cursor(aiomysql.DictCursor)
            ) as cursor:
                await cursor.execute("SELECT * FROM users LIMIT 5;")
                response = await cursor.fetchall()
                five_users: list[RegisteredUser] = []
                for row in response:
                    five_users.append(RegisteredUser(**row))
                return five_users

    async def is_email_address_taken(self, email_address: str) -> bool:
        async with cast(
            aiomysql.Connection, self.mysql_connection_pool.acquire()
        ) as connection:
            async with cast(aiomysql.Cursor, connection.cursor()) as cursor:
                await cursor.execute(
                    "SELECT user_id FROM users WHERE user_email=%(email_address)s",
                    {"email_address": email_address},
                )
                row = await cursor.fetchone()
                if row:
                    return True
                return False

    async def _are_new_user_details_valid_with_reasons(
        self, new_user_details: RegistrationAttempt
    ) -> tuple[bool, dict[str, str]]:
        """
        This function ensures that the new_user_details are valid values. It does not
        (and should not) check that the email address is already being used
        """
        are_details_valid = True
        issues: dict[str, str] = {
            "desired_user_email": "no issues",
            "hashed_user_password": "no issues",
            "desired_human_name": "no issues",
            "desired_ai_name": "no issues",
        }
        # Skipping checking that the email address is taken
        # if await self.is_email_address_taken(new_user_details.desired_user_email):
        #     are_details_valid = False
        #     issues["desired_user_email"] = "email address is taken"
        return are_details_valid, issues

    async def create_user(
        self, new_user_details: RegistrationAttempt
    ) -> RegisteredUser:
        (
            are_new_user_details_valid,
            issues,
        ) = await self._are_new_user_details_valid_with_reasons(new_user_details)
        if not are_new_user_details_valid:
            raise HTTPException(status_code=400, detail=issues)

        async with cast(
            aiomysql.Connection, self.mysql_connection_pool.acquire()
        ) as connection:
            async with cast(
                aiomysql.DictCursor,
                connection.cursor(aiomysql.DictCursor),
            ) as cursor:
                try:
                    await connection.begin()
                    await cursor.execute(
                        "INSERT INTO users (user_email, hashed_user_password, human_name, ai_name, is_user_email_verified) VALUES (%(user_email)s, %(hashed_user_password)s, %(human_name)s, %(ai_name)s, %(is_user_email_verified)s)",
                        {
                            "user_email": new_user_details.desired_user_email,
                            "hashed_user_password": new_user_details.hashed_user_password.get_secret_value(),
                            "human_name": new_user_details.desired_human_name,
                            "ai_name": new_user_details.desired_ai_name,
                            "is_user_email_verified": 0,
                        },
                    )
                except aiomysql.IntegrityError as integrity_error:
                    await connection.rollback()
                    if integrity_error.args[0] == 1062:
                        # This code means we attempted to insert a row that conflicted
                        # with another row. That only happens if the email address is already taken
                        # https://dev.mysql.com/doc/mysql-errors/8.4/en/server-error-reference.html#error_er_dup_entry
                        raise HTTPException(
                            status_code=400, detail="Email already in use."
                        )
                except Exception:
                    await connection.rollback()
                    unexpected_exception_msg = (
                        "Unexpected exception while trying to register a new user"
                    )
                    log.exception(
                        unexpected_exception_msg,
                    )
                    raise HTTPException(
                        status_code=500, detail=unexpected_exception_msg
                    )
                else:
                    await connection.commit()

                await cursor.execute(
                    "SELECT user_id, user_email, hashed_user_password, human_name, ai_name FROM users WHERE user_id=%(user_id)s",
                    {"user_id": cursor.lastrowid},
                )
                new_registered_user_row = await cursor.fetchone()
                return RegisteredUser(**new_registered_user_row)

    # def start_user(self, user: GptHomeUser) -> None:
    #     user.start_gpt_home()

    # def stop_user(self, user: GptHomeUser) -> None:
    #     user.stop_gpt_home()

    # def get_user(self, user_id: str) -> GptHomeUser | None:
    #     pass

    def delete_user(self, user_id: str) -> None:
        pass
        # if self.users.get(user_id):
        #     self.stop_user(self.users[user_id])
        #     if self.users[user_id].gpt_home:
        #         # ensure we free up the memory. prob not necessary tbh
        #         self.users[user_id].gpt_home = None
        #     self.users.pop(user_id)
        #     self._save_users_to_filesystem()

    async def authenticate_user(
        self, user_email: EmailStr, unhashed_user_password: SecretStr
    ):
        async with cast(
            aiomysql.Connection, self.mysql_connection_pool.acquire()
        ) as connection:
            async with cast(
                aiomysql.DictCursor, connection.cursor(aiomysql.DictCursor)
            ) as cursor:
                await cursor.execute(
                    "SELECT hashed_user_password FROM users WHERE user_email=%(user_email)s",
                    {"user_email": user_email},
                )
                row = await cursor.fetchone()
                if row:
                    self.verify_password(
                        unhashed_user_password,
                        hashed_user_password=row["hashed_user_password"],
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to authenticate user {user_email} because they are not a known user.",
                    )

    def _get_hash_of_password(self, unhashed_user_password: SecretStr) -> SecretStr:
        return SecretStr(
            self.pwd_context.hash(unhashed_user_password.get_secret_value())
        )

    def verify_password(
        self, unhashed_user_password: SecretStr, hashed_user_password: SecretStr
    ) -> bool:
        return self.pwd_context.verify(
            unhashed_user_password.get_secret_value(),
            hashed_user_password.get_secret_value(),
        )

    # def get_user_chat_previews(
    #     self, user_id: str, start: int, end: int
    # ) -> list[ChatPreview]:
    #     # if self.users.get(user_id):
    #     #     pass
    #     return []
