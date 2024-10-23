import logging
import asyncpg  # type: ignore[import-untyped]
import asyncpg.cursor  # type: ignore[import-untyped]

from fastapi import HTTPException, status
from rich.logging import RichHandler


from pydantic import BaseModel, EmailStr, Field, SecretStr
from typing import cast

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
    desired_user_password: SecretStr = Field(max_length=32)
    desired_human_name: str = Field(max_length=32)
    desired_ai_name: str = Field(max_length=16)


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
        # TODO error handling if connection fails. Though maybe don't bother because
        # what's the point if the connection fails, lol
        self.postgres_connection_pool: asyncpg.Pool = await asyncpg.create_pool(  # type: ignore[annotation-unchecked]
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres",
            min_size=1,
            max_size=5,
        )
        log.info("Successfully started the users DB connection pool")

        await self._ensure_users_table_is_created_in_db()

    async def _ensure_users_table_is_created_in_db(self) -> None:
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
                # > docker exec -it gpt-home-dev-postgres bash
                # > > psql -U postgres
                # > > > \c postgres
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
                                     """)  # TODO add a field like "is_deactivated" and check it when doing auth so a user can't be deactivated but their token still works
                await connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_user_email ON users(user_email)"
                )
        log.info("Finished ensuring the users table is created")

    async def end(self) -> None:
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
        self,
        desired_user_email: EmailStr,
        hashed_desired_user_password: SecretStr,
        desired_human_name: str,
        desired_ai_name: str,
    ) -> tuple[bool, dict[str, str]]:
        """
        This function ensures that the new_user_details are valid values. It does not
        (and should not need to) check that the email address is already being used
        """
        are_details_valid = True
        issues: dict[str, str] = {
            "desired_user_email": "no issues",
            "hashed_desired_user_password": "no issues",
            "desired_human_name": "no issues",
            "desired_ai_name": "no issues",
        }
        # Skipping checking that the email address is taken, because this happens when
        # we try to insert the row anyways
        return are_details_valid, issues

    async def create_user(
        self,
        desired_user_email: EmailStr,
        hashed_desired_user_password: SecretStr,
        desired_human_name: str,
        desired_ai_name: str,
    ) -> RegisteredUser:
        (
            are_new_user_details_valid,
            issues,
        ) = await self._are_new_user_details_valid_with_reasons(
            desired_user_email,
            hashed_desired_user_password,
            desired_human_name,
            desired_ai_name,
        )
        if not are_new_user_details_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=issues)

        async with self.postgres_connection_pool.acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            try:
                async with connection.transaction():
                    params = {
                        "user_email": desired_user_email,
                        "hashed_user_password": hashed_desired_user_password.get_secret_value(),
                        "human_name": desired_human_name,
                        "ai_name": desired_ai_name,
                        "is_user_email_verified": False,
                    }
                    positional_arg_idxs = ", ".join(
                        f"${idx+1}" for idx in range(len(params))
                    )  # results in "$1, $2, $3, $4, $5"
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
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email address {desired_user_email} already in use.",
                )

    async def get_user_by_email(self, user_email: EmailStr) -> RegisteredUser:
        async with self.postgres_connection_pool.acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            row = await connection.fetchrow(
                "SELECT * FROM users WHERE user_email=$1", user_email
            )
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User {user_email} does not exist.",
                )
            return RegisteredUser(**row)
