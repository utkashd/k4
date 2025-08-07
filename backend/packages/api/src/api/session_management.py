import datetime
import uuid
from typing import Iterable

from backend_commons.postgres_table_manager import (
    IdempotentMigrations,
    PostgresTableManager,
)
from fastapi import HTTPException, status
from pydantic import BaseModel


class SessionInDb(BaseModel):
    session_id: uuid.UUID
    user_id: int
    created_at: datetime.datetime
    last_seen_at: datetime.datetime
    expires_at: datetime.datetime
    user_agent: str
    ip_address: str
    is_active: bool


class SessionsManager(PostgresTableManager):
    @property
    def create_table_queries(self) -> Iterable[str]:
        return [
            """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id UUID PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            user_agent TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true
        )
        """
        ]

    @property
    def create_indexes_queries(self) -> Iterable[str]:
        return [
            "CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id)",
        ]

    @property
    def IDEMPOTENT_MIGRATIONS(self) -> list[IdempotentMigrations]:
        return []

    async def create_session(
        self, user_id: int, user_agent: str, ip_address: str
    ) -> SessionInDb:
        session_id = uuid.uuid4()
        expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=14)
        async with self.get_transaction_connection() as connection:
            new_session = await connection.fetchrow(
                "INSERT INTO sessions (session_id, user_id, expires_at, user_agent, ip_address) VALUES ($1, $2, $3, $4, $5) RETURNING *",
                session_id,
                user_id,
                expires_at,
                user_agent,
                ip_address,
            )
            assert new_session
            return SessionInDb(**new_session)

    async def get_unexpired_session(self, session_id: uuid.UUID) -> SessionInDb:
        async with self.get_connection() as connection:
            row = await connection.fetchrow(
                "SELECT * FROM sessions WHERE session_id=$1 AND expires_at > CURRENT_TIMESTAMP",
                str(session_id),
            )
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No such unexpired session exists (your session probably expired)",
                )
            return SessionInDb(**row)

    async def deactivate_session(self, session_id: uuid.UUID) -> None:
        async with self.get_transaction_connection() as connection:
            await connection.execute(
                "UPDATE sessions SET is_active=false WHERE session_id=$1",
                str(session_id),
            )

    async def deactivate_sessions_by_user(self, user_id: int) -> None:
        # TODO this isn't used anywhere yet
        async with self.get_transaction_connection() as connection:
            await connection.execute(
                "UPDATE sessions SET is_active=false WHERE user_id=$1", user_id
            )
