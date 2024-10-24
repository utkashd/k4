import logging
import asyncpg  # type: ignore[import-untyped]
import asyncpg.cursor  # type: ignore[import-untyped]

from fastapi import HTTPException, status
from rich.logging import RichHandler


from pydantic import BaseModel, EmailStr, Field, SecretStr
from typing import Iterable, cast

from backend_commons import AsyncObject


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class RegisteredUser(BaseModel):
    """
    If you're changing the table, you'll need to drop the existing table
    on your local machine first. Something like:
    > `$ docker exec -it gpt-home-dev-postgres bash`
    > > `$ psql -U postgres`
    > > > `$ \c postgres`
    > > > `$ drop table users;`

    `exit` a couple times to return to your terminal
    """

    user_id: int
    user_email: EmailStr = Field(
        description="idx"
    )  # Hack: I'm using the description to annotate this field and say that I want an index created for it in the DB
    hashed_user_password: SecretStr
    human_name: str = Field(min_length=1, max_length=64)
    ai_name: str = Field(min_length=1, max_length=64)
    is_user_email_verified: bool
    is_user_deactivated: bool
    is_user_an_admin: bool


class AdminUser(RegisteredUser):
    is_user_an_admin: bool = True


class NonAdminUser(RegisteredUser):
    is_user_an_admin: bool = False


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

    def _get_create_users_table_queries(
        self, registered_user_pydantic_model_class: type[BaseModel]
    ) -> tuple[str, Iterable[str]]:
        """
        Currently assumes that:
         1. `user_id` is a special field
         2. `user_email` must be unique
         3. every field is required (`NOT NULL`)
        """
        registered_user_schema = (
            registered_user_pydantic_model_class.model_json_schema()
        )
        """
        Example of the above:

        {
            'properties': {
                'user_id': {'title': 'User Id', 'type': 'integer'},
                'user_email': {'description': 'idx', 'format': 'email', 'title': 'User Email', 'type': 'string'},
                'hashed_user_password': {
                    'format': 'password',
                    'title': 'Hashed User Password',
                    'type': 'string',
                    'writeOnly': True
                },
                'human_name': {'maxLength': 64, 'minLength': 1, 'title': 'Human Name', 'type': 'string'},
                'ai_name': {'maxLength': 64, 'minLength': 1, 'title': 'Ai Name', 'type': 'string'},
                'is_user_email_verified': {'title': 'Is User Email Verified', 'type': 'boolean'},
                'is_user_deactivated': {'title': 'Is User Deactivated', 'type': 'boolean'},
                'is_user_an_admin': {'anyOf': [{'type': 'boolean'}, {'type': 'null'}], 'title': 'Is User An Admin'}
            },
            'required': [
                'user_id',
                'user_email',
                'hashed_user_password',
                'human_name',
                'ai_name',
                'is_user_email_verified',
                'is_user_deactivated',
                'is_user_an_admin'
            ],
            'title': 'RegisteredUser',
            'type': 'object'
        }
        """

        def convert_model_json_schema_property_to_postgres_field(
            prop_name: str, prop_info: dict[str, str | int]
        ):
            if prop_name == "user_id":
                return "user_id SERIAL PRIMARY KEY"
            elif prop_name == "user_email":
                return "user_email VARCHAR(255) NOT NULL UNIQUE"

            match prop_info.get("type"):
                case "string":
                    prop_max_length = prop_info.get("maxLength")
                    if prop_max_length:
                        return f"{prop_name} VARCHAR({prop_max_length}) NOT NULL"
                    else:
                        return f"{prop_name} VARCHAR(255) NOT NULL"
                case "boolean":
                    return f"{prop_name} BOOLEAN NOT NULL"
                case _:
                    raise Exception(
                        f"Unexpected or unimplemented field type in the pydantic model {registered_user_pydantic_model_class}"
                    )

        postgres_columns = ", ".join(
            convert_model_json_schema_property_to_postgres_field(prop_name, prop_info)
            for prop_name, prop_info in registered_user_schema["properties"].items()
        )
        create_users_table_query = (
            f"CREATE TABLE IF NOT EXISTS users ({postgres_columns})"
        )

        create_index_queries = []
        for prop_name, prop_info in registered_user_schema["properties"].items():
            if prop_info.get("description") == "idx":
                create_index_queries.append(
                    f"CREATE INDEX IF NOT EXISTS idx_{prop_name} ON users({prop_name})"
                )

        return (
            create_users_table_query,
            create_index_queries,
        )

    async def _ensure_users_table_is_created_in_db(self) -> None:
        log.info(
            """Creating the users table if it doesn't already exist. You may see a
            warning from aiomysql that the table already exists, this is expected and
            harmless."""
        )
        async with self.postgres_connection_pool.acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            async with connection.transaction():
                # TODO should have a script or something for modifying tables elegantly
                create_users_table_query, create_index_queries = (
                    self._get_create_users_table_queries(RegisteredUser)
                )
                await connection.execute(create_users_table_query)
                for create_index_query in create_index_queries:
                    await connection.execute(create_index_query)
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

    async def create_user(
        self,
        desired_user_email: EmailStr,
        hashed_desired_user_password: SecretStr,
        desired_human_name: str,
        desired_ai_name: str,
    ) -> NonAdminUser:
        async def _are_new_user_details_valid_with_reasons(
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

        (
            are_new_user_details_valid,
            issues,
        ) = await _are_new_user_details_valid_with_reasons(
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
                    user = NonAdminUser(
                        user_id=0,
                        user_email=desired_user_email,
                        hashed_user_password=hashed_desired_user_password,
                        human_name=desired_human_name,
                        ai_name=desired_ai_name,
                        is_user_email_verified=False,
                        is_user_an_admin=False,
                        is_user_deactivated=False,
                    )
                    user_row_params = user.model_dump()
                    for key, value in user_row_params.items():
                        if isinstance(value, SecretStr):
                            user_row_params[key] = value.get_secret_value()
                    positional_arg_idxs = ", ".join(
                        f"${idx+1}" for idx in range(len(user_row_params))
                    )  # results in "$1, $2, $3, $4, $5"
                    query = f'INSERT INTO USERS ({', '.join(user_row_params)}) VALUES ({positional_arg_idxs}) RETURNING *'
                    # query = "INSERT INTO users (user_email, hashed_user_password,
                    # human_name, ai_name, is_user_email_verified) VALUES ($1, $2, $3,
                    # $4, $5) RETURNING *"
                    new_registered_user_row = await connection.fetchrow(
                        query, *user_row_params.values()
                    )
                    return NonAdminUser(**new_registered_user_row)
            except asyncpg.exceptions.UniqueViolationError:
                # This code means we attempted to insert a row that conflicted
                # with another row. That only happens if the email address is already taken
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email address {desired_user_email} already in use.",
                )

    async def get_user_by_email(self, user_email: EmailStr) -> AdminUser | NonAdminUser:
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
            user = RegisteredUser(**row)
            if user.is_user_deactivated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"User {user.user_email} is a deactivated user.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if user.is_user_an_admin:
                return AdminUser(**user.model_dump())
            else:
                return NonAdminUser(**user.model_dump())
