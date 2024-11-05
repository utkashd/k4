import logging
from datetime import datetime
from typing import Iterable

from backend_commons import PostgresTableManager
from rich.logging import RichHandler


from pydantic import BaseModel, Field


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class MessageInDb(BaseModel):
    message_id: int
    chat_id: int = Field(description="idx")
    user_id: int
    text: str
    inserted_at: datetime


class MessagesManager(PostgresTableManager):
    @property
    def create_table_query(self) -> str:
        # Creating foreign keys syntax: https://stackoverflow.com/questions/28558920/postgresql-foreign-key-syntax
        return """
        CREATE TABLE IF NOT EXISTS messages (
            message_id SERIAL PRIMARY KEY,
            chat_id INT NOT NULL,
            user_id INT NOT NULL REFERENCES users (user_id),
            text TEXT NOT NULL,
            inserted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """

    @property
    def create_indexes_queries(self) -> Iterable[str]:
        return ("CREATE INDEX IF NOT EXISTS idx_chat_id ON messages(chat_id)",)

    async def save_client_message_to_db(
        self, chat_id: int, user_id: int, text: str
    ) -> MessageInDb:
        async with self.get_transaction_connection() as connection:
            new_message = await connection.fetchrow(
                "INSERT INTO messages (chat_id, user_id, text) VALUES ($1, $2, $3) RETURNING *",
                chat_id,
                user_id,
                text,
            )
            return MessageInDb(**new_message)

    async def save_gpt_home_message_to_db(self, chat_id: int, text: str) -> MessageInDb:
        async with self.get_transaction_connection() as connection:
            new_message = await connection.fetchrow(
                "INSERT INTO messages (chat_id, user_id, text) VALUES ($1, $2, $3) RETURNING *",
                chat_id,
                0,  # 0 signifies gpt_home? prob a bad pattern
                text,
            )
            return MessageInDb(**new_message)

    async def get_messages_of_chat(self, chat_id: int) -> Iterable[MessageInDb]:
        async with self.get_connection() as connection:
            records = await connection.fetch(
                "SELECT * FROM messages WHERE chat_id=$1", chat_id
            )
            return [MessageInDb(**record) for record in records]
