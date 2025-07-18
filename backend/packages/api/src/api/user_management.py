import asyncpg  # type: ignore[import-untyped,unused-ignore]
from backend_commons import PostgresTableManager
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr


class RegisteredUser(BaseModel):
    # If you're changing the table, you'll need to drop the existing table
    # on your local machine first. Something like:
    # > `$ docker exec -it k4-dev-postgres bash`
    # > > `$ psql -U postgres`
    # > > > `$ \c postgres` # connect to the DB named "postgres"
    # > > > `$ \d` # show the tables
    # > > > `$ drop table users;`
    # `exit` a couple times to return to your terminal

    user_id: int
    user_email: EmailStr
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
    desired_user_password: SecretStr = Field(max_length=64)
    desired_human_name: str = Field(max_length=64)
    desired_ai_name: str = Field(max_length=64)


class UsersManager(PostgresTableManager):
    """
    This class is intended to be instantiated like so:

    ```
    users_manager = UsersManager()
    connection_pool: asyncpg.Pool = await asyncpg.create_pool(...)
    users_manager.set_connection_pool_and_start(connection_pool)
    # now it's usable
    ```
    """

    def __init__(self) -> None:
        self._does_at_least_one_active_admin_user_exist = False
        super().__init__()

    @property
    def create_table_queries(self) -> list[str]:
        # TODO replace the varchar(x) with text datatype and CHECK clauses
        return [
            """
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL UNIQUE,
            hashed_user_password VARCHAR(255) NOT NULL,
            human_name VARCHAR(64) NOT NULL,
            ai_name VARCHAR(64),
            is_user_email_verified BOOLEAN NOT NULL,
            is_user_deactivated BOOLEAN NOT NULL,
            is_user_an_admin BOOLEAN NOT NULL
        )
        """
        ]

    @property
    def create_indexes_queries(self) -> tuple[str]:
        return ("CREATE INDEX IF NOT EXISTS idx_user_email ON users(user_email)",)

    async def does_at_least_one_active_admin_user_exist(self) -> bool:
        if self._does_at_least_one_active_admin_user_exist:
            return True
        async with self.get_connection() as connection:
            admin_user_or_none = await connection.fetchrow(
                "SELECT * FROM users WHERE is_user_deactivated=false AND is_user_an_admin=true LIMIT 1"
            )
            if admin_user_or_none:
                self._does_at_least_one_active_admin_user_exist
                return True
            return False

    async def create_user(
        self,
        desired_user_email: EmailStr,
        hashed_desired_user_password: SecretStr,
        desired_human_name: str,
        desired_ai_name: str,
        is_user_an_admin: bool = False,
    ) -> RegisteredUser:
        def _are_new_user_details_valid_with_reasons(
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
        ) = _are_new_user_details_valid_with_reasons(
            desired_user_email,
            hashed_desired_user_password,
            desired_human_name,
            desired_ai_name,
        )
        if not are_new_user_details_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=issues)

        async with self.get_transaction_connection() as connection:
            try:
                user = RegisteredUser(
                    user_id=0,
                    user_email=desired_user_email,
                    hashed_user_password=hashed_desired_user_password,
                    human_name=desired_human_name,
                    ai_name=desired_ai_name,
                    is_user_email_verified=False,
                    is_user_an_admin=is_user_an_admin,
                    is_user_deactivated=False,
                )
                user_row_params = user.model_dump()
                user_row_params.pop("user_id")  # Let the DB assign a user_id
                for key, value in user_row_params.items():
                    if isinstance(value, SecretStr):
                        user_row_params[key] = value.get_secret_value()
                positional_arg_idxs = ", ".join(
                    f"${idx + 1}" for idx in range(len(user_row_params))
                )  # results in "$1, $2, $3, $4, $5"
                query = f"INSERT INTO USERS ({', '.join(user_row_params)}) VALUES ({positional_arg_idxs}) RETURNING *"
                # query = "INSERT INTO users (user_email, hashed_user_password,
                # human_name, ai_name, is_user_email_verified) VALUES ($1, $2, $3,
                # $4, $5) RETURNING *"
                new_registered_user_row = await connection.fetchrow(
                    query, *user_row_params.values()
                )
                if not new_registered_user_row:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Unexpectedly could not insert a new user {user.user_email=} into the database.",
                    )
                if is_user_an_admin:
                    return AdminUser(**new_registered_user_row)
                return NonAdminUser(**new_registered_user_row)
            except asyncpg.exceptions.UniqueViolationError:
                # This code means we attempted to insert a row that conflicted
                # with another row. That only happens if the email address is already taken
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email address {desired_user_email} already in use.",
                )

    async def get_user_by_user_id(self, user_id: int) -> AdminUser | NonAdminUser:
        async with self.get_connection() as connection:
            row = await connection.fetchrow(
                "SELECT * FROM users WHERE user_id=$1", user_id
            )
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User with {user_id=} does not exist.",
                )
            user = RegisteredUser(**row)
            if user.is_user_an_admin:
                return AdminUser(**user.model_dump())
            else:
                return NonAdminUser(**user.model_dump())

    async def get_active_user_by_email(
        self, user_email: EmailStr
    ) -> AdminUser | NonAdminUser:
        user = await self.get_active_or_inactive_user_by_email(user_email)
        if user.is_user_deactivated:
            raise HTTPException(
                # TODO this might be the wrong status code
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User {user.user_email} is a deactivated user.",
            )
        return user

    async def get_active_or_inactive_user_by_email(
        self, user_email: EmailStr
    ) -> AdminUser | NonAdminUser:
        async with self.get_connection() as connection:
            row = await connection.fetchrow(
                "SELECT * FROM users WHERE user_email=$1", user_email
            )
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User {user_email} does not exist.",
                )
            user = RegisteredUser(**row)
            if user.is_user_an_admin:
                return AdminUser(**user.model_dump())
            else:
                return NonAdminUser(**user.model_dump())

    async def get_users(self) -> list[RegisteredUser]:
        """
        Meant only for admins, so we're just returning all users indiscriminantely
        """
        # TODO paginate
        # TODO require admin user is passed here, log it
        users: list[RegisteredUser] = []
        async with self.get_connection() as connection:
            rows = await connection.fetch("SELECT * from USERS limit 50")
            for row in rows:
                users.append(RegisteredUser(**row))
            return users

    async def deactivate_user(self, user_to_deactivate: RegisteredUser) -> None:
        """
        Meant only for admins
        """
        # TODO require admin user is passed here, log it
        async with self.get_transaction_connection() as connection:
            await connection.execute(
                "UPDATE users SET is_user_deactivated=true WHERE user_id=$1",
                user_to_deactivate.user_id,
            )

    async def reactivate_user(self, user_to_reactivate: RegisteredUser) -> None:
        """
        Meant only for admins
        """
        # TODO require admin user is passed here, log it
        async with self.get_transaction_connection() as connection:
            await connection.execute(
                "UPDATE users SET is_user_deactivated=false WHERE user_id=$1",
                user_to_reactivate.user_id,
            )
