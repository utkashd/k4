import logging
import asyncpg  # type: ignore[import-untyped]
import asyncpg.cursor  # type: ignore[import-untyped]

# from backend_commons.messages import Message
# from gpt_home.gpt_home import GptHomeDebugOptions
# from gpt_home.gpt_home_human import GptHomeHuman
from fastapi import HTTPException
from rich.logging import RichHandler

# from gpt_home.utils.file_io import get_gpt_home_root_directory
# import os
# from pathlib import Path
# from gpt_home import GptHome

# from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, SecretStr  # , RootModel
from typing import cast  # , Literal

from backend_commons import AsyncObject


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
    is_user_email_verified: bool


class RegistrationAttempt(BaseModel):
    """
    Holds attributes corresponding to a new user attempting to register.
    """

    desired_user_email: EmailStr
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
        self.postgres_connection_pool: asyncpg.Pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres",
            min_size=1,
            max_size=5,
        )
        if self.postgres_connection_pool:  # `.is_serving()` is not implemented
            log.info("Successfully started the users DB connection pool")

        await self._ensure_users_table_is_created_in_db()

    async def _ensure_users_table_is_created_in_db(self):
        log.info(
            """Creating the users table if it doesn't already exist. You may see a
            warning from aiomysql that the table already exists, this is expected and
            harmless."""
        )
        async with self.postgres_connection_pool.acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            async with connection.transaction():
                # If you're changing the table, you'll need to drop the existing table
                # on your local machine first. Something like:
                # > docker exec -it mysql-dev bash
                # > > mysql -u root -p # the password is in <repo root>/start_dev.sh
                # > > > drop table mydb.users;
                # `exit` a couple times to return to your terminal
                # TODO should have a script or something for modifying tables elegantly
                await connection.execute("""
                                     CREATE TABLE IF NOT EXISTS users 
                                     (
                                     user_id SERIAL PRIMARY KEY,
                                     user_email VARCHAR(255) NOT NULL UNIQUE,
                                     hashed_user_password VARCHAR(255) NOT NULL,
                                     human_name VARCHAR(255) NOT NULL,
                                     ai_name VARCHAR(255),
                                     is_user_email_verified BOOLEAN NOT NULL
                                     )
                                     """)
                await connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_email ON users(user_email)"
                )
        log.info("Finished ensuring the users table is created")

    async def end(self):
        log.info("Closing the users DB connection pool")
        await self.postgres_connection_pool.close()

    async def get_five_users_async(self) -> list[RegisteredUser]:
        """
        This method is just used for testing stuff and can be deleted eventually
        """
        async with self.postgres_connection_pool.acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            query_response = await connection.fetch("SELECT * FROM users LIMIT 5")
            five_users: list[RegisteredUser] = []
            for row in query_response:
                five_users.append(RegisteredUser(**row))
            return five_users

    # async def is_email_address_taken(self, email_address: EmailStr) -> bool:
    #     if await self._get_user_fields_by_user_email(email_address, {"user_id"}):
    #         return True
    #     return False

    async def _are_new_user_details_valid_with_reasons(
        self, new_user_details: RegistrationAttempt
    ) -> tuple[bool, dict[str, str]]:
        """
        This function ensures that the new_user_details are valid values. It does not
        (and should not need to) check that the email address is already being used
        """
        are_details_valid = True
        issues: dict[str, str] = {
            "desired_user_email": "no issues",
            "hashed_user_password": "no issues",
            "desired_human_name": "no issues",
            "desired_ai_name": "no issues",
        }
        # Skipping checking that the email address is taken, because this happens when
        # we try to insert the row anyways
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

        async with self.postgres_connection_pool.acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            try:
                async with connection.transaction():
                    params = {
                        "user_email": new_user_details.desired_user_email,
                        "hashed_user_password": new_user_details.hashed_user_password.get_secret_value(),
                        "human_name": new_user_details.desired_human_name,
                        "ai_name": new_user_details.desired_ai_name,
                        "is_user_email_verified": False,
                    }
                    positional_arg_idxs = ", ".join(
                        f"${idx+1}" for idx in range(len(params))
                    )
                    query = f'INSERT INTO USERS ({', '.join(params)}) VALUES ({positional_arg_idxs}) RETURNING *'
                    # query = "INSERT INTO users (user_email, hashed_user_password, human_name, ai_name, is_user_email_verified) VALUES ($1, $2, $3, $4, $5) RETURNING *"
                    new_registered_user_row = await connection.fetchrow(
                        query, *params.values()
                    )
                    return RegisteredUser(**new_registered_user_row)
            except asyncpg.exceptions.UniqueViolationError:
                # This code means we attempted to insert a row that conflicted
                # with another row. That only happens if the email address is already taken
                raise HTTPException(
                    status_code=400, detail="Email address already in use."
                )

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

        """
        user_id INT AUTO_INCREMENT PRIMARY KEY,
                                     user_email VARCHAR(255) NOT NULL UNIQUE,
                                     hashed_user_password VARCHAR(255) NOT NULL,
                                     human_name VARCHAR(255) NOT NULL,
                                     ai_name VARCHAR(255),
                                     is_user_email_verified BOOLEAN NOT NULL,
        """

    # async def _get_user_by_user_email(
    #     self,
    #     email_address: EmailStr,
    # ) -> RegisteredUser | None:
    #     async with cast(
    #         asyncpg.Connection, self.postgres_connection_pool.acquire()
    #     ) as connection:
    #         async with cast(
    #             aiomysql.DictCursor, connection.cursor(aiomysql.DictCursor)
    #         ) as cursor:
    #             await cursor.execute(
    #                 "SELECT * FROM users WHERE user_email=%(user_email)s",
    #                 {"user_email": email_address},
    #             )
    #             row = await cursor.fetchone()
    #             if row:
    #                 return RegisteredUser(**row)
    #             else:
    #                 return None

    # async def _get_user_fields_by_user_email(
    #     self,
    #     email_address: EmailStr,
    #     fields: set[
    #         Literal[
    #             "user_id",
    #             "user_email",
    #             "hashed_user_password",
    #             "human_name",
    #             "ai_name",
    #             "is_user_email_verified",
    #         ]
    #     ],
    # ) -> dict[str, int | str | bool] | None:
    #     log.warning(
    #         "This function is untested and not great as-is. Use sparingly until it's fixed"
    #     )
    #     if not fields:
    #         raise HTTPException(
    #             status_code=400, detail="Requested no user fields, which is invalid"
    #         )
    #     valid_fields = {
    #         "user_id",
    #         "user_email",
    #         "hashed_user_password",
    #         "human_name",
    #         "ai_name",
    #         "is_user_email_verified",
    #     }
    #     for field in fields:
    #         if field not in valid_fields:
    #             raise HTTPException(
    #                 status_code=400, detail=f"Requested an invalid user field: {field}"
    #             )

    #     async with cast(
    #         asyncpg.Connection, self.postgres_connection_pool.acquire()
    #     ) as connection:
    #         async with cast(
    #             aiomysql.DictCursor, connection.cursor(aiomysql.DictCursor)
    #         ) as cursor:
    #             await cursor.execute(
    #                 " ".join(
    #                     (
    #                         "SELECT",
    #                         ", ".join(fields),
    #                         "FROM users WHERE user_email=%(user_email)s",
    #                     )
    #                 ),
    #                 {"user_email": email_address},
    #             )
    #             row = await cursor.fetchone()
    #             if row:
    #                 return row
    #             else:
    #                 return None

    # def get_user_chat_previews(
    #     self, user_id: str, start: int, end: int
    # ) -> list[ChatPreview]:
    #     # if self.users.get(user_id):
    #     #     pass
    #     return []
