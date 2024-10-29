import logging
import asyncpg  # type: ignore[import-untyped]

from rich.logging import RichHandler


from pydantic import BaseModel
from typing import Iterable, cast


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class PostgresTableManager:
    """
    A thin class that:
    - accepts a table name, a schema in the form of a Pydantic `BaseModel`, and an
    `asyncpg.Pool` to use to connect to the db
    - ensures the table is created
    - provides *very* basic convenience methods common to interacting with a DB table

    This class is not in a mature state, please read everything before using it

    ```
    users_manager = UsersManager("users")
    connection_pool: asyncpg.Pool = await asyncpg.create_pool(...)
    users_manager.set_connection_pool_and_start(connection_pool)
    # now it's usable
    ```
    """

    def __init__(self) -> None:
        self.postgres_connection_pool: asyncpg.Pool | None = None

    def _get_table_name(self) -> str:
        raise NotImplementedError("You need to implement this method")

    def _get_pydantic_schema(self) -> type[BaseModel]:
        raise NotImplementedError("You need to implement this method")

    async def set_connection_pool_and_start(self, connection_pool: asyncpg.Pool):
        self.postgres_connection_pool = connection_pool
        await self._ensure_table_is_created_in_db()

    def get_connection_pool(self) -> asyncpg.Pool:
        if self.postgres_connection_pool:
            return self.postgres_connection_pool
        raise Exception("Connection pool was not provided.")

    def _get_create_table_queries(
        self, pydantic_schema: type[BaseModel]
    ) -> tuple[str, Iterable[str]]:
        """
        Currently assumes that:
         1. The first field ending with `_id` means that column is `SERIAL PRIMARY KEY`
         2. every field is required (`NOT NULL`)
        """
        pydantic_schema_json = pydantic_schema.model_json_schema()
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
            prop_name: str, prop_info: dict[str, str | int | bool]
        ):
            if len(prop_name) >= 3 and prop_name[-3:] == "_id":
                return f"{prop_name} SERIAL PRIMARY KEY"

            match prop_info.get("type"):
                case "string":
                    description = prop_info.get("description") or ""
                    assert isinstance(description, str)
                    if description:
                        if "unique" in description.split(" "):
                            unique = " UNIQUE"
                        else:
                            unique = ""
                    prop_max_length = prop_info.get("maxLength") or 255
                    return f"{prop_name} VARCHAR({prop_max_length}) NOT NULL{unique}"
                case "boolean":
                    return f"{prop_name} BOOLEAN NOT NULL"
                case _:
                    raise Exception(
                        f"Unexpected or unimplemented field type in the pydantic model {pydantic_schema}"
                    )

        postgres_columns = ", ".join(
            convert_model_json_schema_property_to_postgres_field(prop_name, prop_info)
            for prop_name, prop_info in pydantic_schema_json["properties"].items()
        )
        create_table_query = (
            f"CREATE TABLE IF NOT EXISTS {self._get_table_name()} ({postgres_columns})"
        )

        create_index_queries = []
        for prop_name, prop_info in pydantic_schema_json["properties"].items():
            description: str = prop_info.get("description")
            if "idx" in description.split(" "):
                create_index_queries.append(
                    f"CREATE INDEX IF NOT EXISTS idx_{prop_name} ON {self._get_table_name()}({prop_name})"
                )

        return (
            create_table_query,
            create_index_queries,
        )

    async def _ensure_table_is_created_in_db(self) -> None:
        log.info(
            f"""Creating the {self._get_table_name()} table if it doesn't already exist. You
             may see a warning from aiomysql that the table already exists, this is
             expected and harmless."""
        )
        async with self.get_connection_pool().acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            async with connection.transaction():
                # TODO should have a script or something for modifying tables elegantly
                create_table_query, create_index_queries = (
                    self._get_create_table_queries(self._get_pydantic_schema())
                )
                await connection.execute(create_table_query)
                for create_index_query in create_index_queries:
                    await connection.execute(create_index_query)
        log.info(f"Finished ensuring the {self._get_table_name()} table is created")
