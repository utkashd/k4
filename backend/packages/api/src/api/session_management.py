import datetime
import uuid
from typing import Iterable

from backend_commons.postgres_table_manager import PostgresTableManager
from fastapi import HTTPException, status
from pydantic import BaseModel


class SessionInDb(BaseModel):
    session_id: uuid.UUID


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
            if not new_session:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unexpectedly could not create the session. {session_id=} {user_id=}",
                )
            new_session_in_db = SessionInDb(**new_session)

            return new_session_in_db
