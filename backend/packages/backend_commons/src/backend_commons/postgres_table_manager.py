from contextlib import asynccontextmanager
import logging
import asyncpg  # type: ignore[import-untyped]
from rich.logging import RichHandler
from typing import Iterable, cast


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")


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

    @property
    def create_table_queries(self) -> Iterable[str]:
        raise NotImplementedError("You need to define the table creation query")

    @property
    def create_indexes_queries(self) -> Iterable[str]:
        raise NotImplementedError("You need to define the index creation queries")

    def _get_connection_pool(self) -> asyncpg.Pool:
        if self.postgres_connection_pool:
            return self.postgres_connection_pool
        raise NotImplementedError(
            "Connection pool was not provided. You need to implement this method"
        )

    async def set_connection_pool_and_start(self, connection_pool: asyncpg.Pool):
        self.postgres_connection_pool = connection_pool
        await self._ensure_table_is_created_in_db()

    async def _ensure_table_is_created_in_db(self) -> None:
        log.info(
            f"""Creating the {self.__class__.__name__} table if it doesn't already exist. You
             may see a warning from aiomysql that the table already exists, this is
             expected and harmless."""
        )
        async with self.get_transaction_connection() as connection:
            # TODO should have a script or something for modifying tables elegantly
            for create_table_query in self.create_table_queries:
                await connection.execute(create_table_query)
            for create_index_query in self.create_indexes_queries:
                await connection.execute(create_index_query)
        log.info(f"Finished ensuring the {self.__class__.__name__} table is created")

    @asynccontextmanager
    async def get_connection(self):
        """
        Acquire a Postgres connection

        Better for `SELECT` and other read methods
        """
        async with self._get_connection_pool().acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            yield connection

    @asynccontextmanager
    async def get_transaction_connection(self):
        """
        Acquire a Postgres connection and execute a transaction

        Better for `INSERT` and other write methods
        """
        async with self._get_connection_pool().acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            async with connection.transaction():
                yield connection
