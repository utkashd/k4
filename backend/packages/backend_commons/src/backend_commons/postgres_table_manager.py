from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Iterable

import asyncpg
from k4_logger import log


@dataclass
class IdempotentMigration:
    name: str
    query_or_queries: str | list[str]


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
        self.postgres_connection_pool: "asyncpg.Pool[asyncpg.Record] | None" = None

    # I believe the order of property(abstractmethod(function)) matters here
    @property
    @abstractmethod
    def create_table_queries(self) -> Iterable[str]: ...

    # I believe the order of property(abstractmethod(function)) matters here
    @property
    @abstractmethod
    def create_indexes_queries(self) -> Iterable[str]: ...

    def _get_connection_pool(self) -> "asyncpg.Pool[asyncpg.Record]":
        if self.postgres_connection_pool:
            return self.postgres_connection_pool
        raise NotImplementedError(
            "Connection pool was not provided. You must call `set_connection_pool_and_start` after instatiating."
        )

    @property
    @abstractmethod
    def IDEMPOTENT_MIGRATIONS(self) -> list[IdempotentMigration]: ...

    async def _perform_migrations_if_any(self) -> None:
        """
        Here we run any version-to-version migrations that need to take place.

        "Why don't you just use SqlAlchemy + Alembic?"

        I think it's easy to forget the advantages of using raw SQL as strings:
            - transparency: we know *exactly* what queries are being run in Postgres
            - trading risks: raw SQL strings feel risky, but abstracted queries carry other
            risks. And if something goes wrong, it's going to be tougher to fix issues
            originating from bad SqlAlchemy vs. bad raw queries
            - inertia: I'll never be able to completely forget about SQL. Might as well stay
            sharp and embrace the low-level

        All that, plus raw SQL is lightweight. ORMs are heavy and the featureset can be
        overwhelming and thus confusing. With raw SQL, everything is deliberate, and I'm
        forced to understand what I'm doing
        """

        log.info(f"Running {len(self.IDEMPOTENT_MIGRATIONS)} migrations")

        async with self.get_transaction_connection() as connection:
            for idempotent_migration in self.IDEMPOTENT_MIGRATIONS:
                log.info(f"Starting migration {idempotent_migration.name}")
                if isinstance(idempotent_migration.query_or_queries, str):
                    await connection.execute(idempotent_migration.query_or_queries)
                else:
                    for idempotent_query in idempotent_migration.query_or_queries:
                        await connection.execute(idempotent_query)
                log.info(f"Completed migration {idempotent_migration.name}")

        log.info(f"Finished running {len(self.IDEMPOTENT_MIGRATIONS)} migrations")

    async def set_connection_pool_and_run_migrations_and_start(
        self, connection_pool: "asyncpg.Pool[asyncpg.Record]"
    ) -> None:
        self.postgres_connection_pool = connection_pool
        await self._perform_migrations_if_any()
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
    async def get_connection(
        self,
    ) -> AsyncGenerator["asyncpg.pool.PoolConnectionProxy[asyncpg.Record]", Any]:
        """
        Acquire a Postgres connection

        Better for `SELECT` and other read methods
        """
        async with self._get_connection_pool().acquire() as connection:
            yield connection

    @asynccontextmanager
    async def get_transaction_connection(
        self,
    ) -> AsyncGenerator["asyncpg.pool.PoolConnectionProxy[asyncpg.Record]", Any]:
        """
        Acquire a Postgres connection and execute a transaction

        Better for `INSERT` and other write methods
        """
        async with self._get_connection_pool().acquire() as connection:
            async with connection.transaction():
                yield connection
