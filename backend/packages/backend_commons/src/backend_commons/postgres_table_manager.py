from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Iterable, cast

import asyncpg  # type: ignore[import-untyped,unused-ignore]
from cyris_logger import log


class PostgresTableManager(ABC):
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
    @abstractmethod
    def create_table_queries(self) -> Iterable[str]: ...

    @property
    @abstractmethod
    def create_indexes_queries(self) -> Iterable[str]: ...

    def _get_connection_pool(self) -> asyncpg.Pool:
        if self.postgres_connection_pool:
            return self.postgres_connection_pool
        raise NotImplementedError(
            "Connection pool was not provided. You must call `set_connection_pool_and_start` after instatiating."
        )

    async def set_connection_pool_and_start(
        self, connection_pool: asyncpg.Pool
    ) -> None:
        self.postgres_connection_pool = connection_pool
        await self._ensure_table_is_created_in_db()

    async def _ensure_table_is_created_in_db(self) -> None:
        log.info(
            (
                f"Creating the {self.__class__.__name__} table if it doesn't already "
                "exist. You may see a warning from aiomysql that the table already exists, "
                "this is expected and harmless."
            )
        )
        async with self.get_transaction_connection() as connection:
            # TODO should have a script or something for modifying tables elegantly
            for create_table_query in self.create_table_queries:
                await connection.execute(create_table_query)
            for create_index_query in self.create_indexes_queries:
                await connection.execute(create_index_query)
        log.info(f"Finished ensuring the {self.__class__.__name__} table is created")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, Any]:
        """
        Acquire a Postgres connection

        Better for `SELECT` and other read methods
        """
        async with self._get_connection_pool().acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            yield connection

    @asynccontextmanager
    async def get_transaction_connection(
        self,
    ) -> AsyncGenerator[asyncpg.Connection, Any]:
        """
        Acquire a Postgres connection and execute a transaction

        Better for `INSERT` and other write methods
        """
        async with self._get_connection_pool().acquire() as connection:
            connection = cast(asyncpg.Connection, connection)
            async with connection.transaction():
                yield connection
