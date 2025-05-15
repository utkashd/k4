import datetime
from typing import Iterable

from backend_commons import PostgresTableManager
from backend_commons.messages import MessageInDb
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class ChatInDb(BaseModel):
    chat_id: int
    user_id: int
    title: str = Field(max_length=32)
    last_message_timestamp: datetime.datetime
    is_archived: bool


class Chat(BaseModel):
    messages: list[MessageInDb]
    chat_in_db: ChatInDb


class ChatPreview(BaseModel):
    chat_in_db: ChatInDb
    most_recent_message_in_db: MessageInDb


class MessagesManager(PostgresTableManager):
    @property
    def create_table_queries(self) -> list[str]:
        # If you're changing the tables, you'll need to drop the existing table
        # on your local machine first. Something like:
        # > `$ docker exec -it k4-dev-postgres bash`
        # > > `$ psql -U postgres`
        # > > > `$ \c postgres` # connect to the DB named "postgres"
        # > > > `$ \d` # show the tables
        # > > > `$ drop table messages;`
        # `exit` a couple times to return to your terminal

        # Creating foreign keys syntax:
        # https://stackoverflow.com/questions/28558920/postgresql-foreign-key-syntax
        # In the messages table, a null value for user_id indicates the message was sent
        # by k4 (and not by a user)
        return [
            """
        CREATE TABLE IF NOT EXISTS chats (
            chat_id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users (user_id),
            title VARCHAR(32) NOT NULL,
            last_message_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            is_archived BOOLEAN NOT NULL
        )
        """,
            """
        CREATE TABLE IF NOT EXISTS messages (
            message_id SERIAL PRIMARY KEY,
            chat_id INT NOT NULL REFERENCES chats (chat_id),
            user_id INT REFERENCES users (user_id),
            text TEXT NOT NULL,
            inserted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """,
        ]

    @property
    def create_indexes_queries(self) -> Iterable[str]:
        return (
            "CREATE INDEX IF NOT EXISTS idx_user_id ON chats(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_id ON messages(chat_id)",
        )

    async def create_new_chat(self, user_id: int, title: str) -> ChatInDb:
        if len(title) > 32:
            title = title[:29] + "..."
        async with self.get_transaction_connection() as connection:
            new_chat = await connection.fetchrow(
                "INSERT INTO chats (user_id, title, is_archived) VALUES ($1, $2, $3) RETURNING *",
                user_id,
                title,
                False,
            )
            if not new_chat:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpectedly could not add the chat to the database.",
                )
            return ChatInDb(**new_chat)

    async def delete_chat(self, chat_id: int) -> None:
        async with self.get_transaction_connection() as connection:
            await connection.execute("DELETE FROM messages WHERE chat_id=$1", chat_id)
            await connection.execute("DELETE FROM chats WHERE chat_id=$1", chat_id)

    async def _save_message_to_db(
        self, chat_id: int, user_id: int | None, text: str
    ) -> MessageInDb:
        """
        Parameters
        ----------
        user_id : int | None
            `None` iff the message is from k4
        """
        async with self.get_transaction_connection() as connection:
            new_message = await connection.fetchrow(
                "INSERT INTO messages (chat_id, user_id, text) VALUES ($1, $2, $3) RETURNING *",
                chat_id,
                user_id,
                text,
            )
            if not new_message:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unexpectedly could not save the message to the database. {chat_id=} {user_id=}",
                )
            new_message_in_db = MessageInDb(**new_message)
            await connection.execute(
                "UPDATE chats SET last_message_timestamp=$1 WHERE chat_id=$2",
                new_message_in_db.inserted_at,
                new_message_in_db.chat_id,
            )
            return new_message_in_db

    async def save_client_message_to_db(
        self, chat_id: int, user_id: int, text: str
    ) -> MessageInDb:
        return await self._save_message_to_db(
            chat_id=chat_id, user_id=user_id, text=text
        )

    async def save_k4_message_to_db(self, chat_id: int, text: str) -> MessageInDb:
        return await self._save_message_to_db(chat_id=chat_id, user_id=None, text=text)

    async def get_user_chat_previews(
        self,
        user_id: int,
        num_chats: int,
        # after_timestamp: datetime.datetime, # TODO implement this
    ) -> list[ChatPreview]:
        async with self.get_connection() as connection:
            chats = await connection.fetch(
                "SELECT * FROM chats WHERE user_id=$1 ORDER BY last_message_timestamp DESC LIMIT $2",
                user_id,
                num_chats,
            )
            chat_previews = []
            for chat in chats:
                chat_id = ChatInDb(**chat).chat_id
                latest_message = await connection.fetchrow(
                    "SELECT * FROM messages WHERE chat_id=$1 ORDER BY inserted_at DESC LIMIT 1",
                    chat_id,
                )
                if not latest_message:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No messages found in the database for chat {chat_id=}",
                    )
                chat_previews.append(
                    ChatPreview(
                        chat_in_db=ChatInDb(**chat),
                        most_recent_message_in_db=MessageInDb(**latest_message),
                    )
                )
            return chat_previews

    async def does_user_own_this_chat(self, user_id: int, chat_id: int) -> bool:
        async with self.get_connection() as connection:
            val: int = await connection.fetchval(
                "SELECT user_id FROM chats WHERE chat_id=$1", chat_id
            )
            return user_id == val

    async def get_chat(self, chat_id: int) -> Chat:
        return Chat(
            chat_in_db=await self.get_chat_in_db(chat_id=chat_id),
            messages=await self.get_messages_of_chat(chat_id=chat_id),
        )

    async def get_chat_in_db(self, chat_id: int) -> ChatInDb:
        async with self.get_connection() as connection:
            chat = await connection.fetchrow(
                "SELECT * FROM chats WHERE chat_id=$1", chat_id
            )
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No chat with {chat_id=} was found in the database.",
                )
            return ChatInDb(**chat)

    async def get_messages_of_chat(
        self, chat_id: int, limit: int | None = None
    ) -> list[MessageInDb]:
        async with self.get_connection() as connection:
            if limit:
                records = await connection.fetch(
                    "SELECT * FROM messages WHERE chat_id=$1 ORDER BY inserted_at DESC LIMIT $2",
                    chat_id,
                    limit,
                )
            else:
                records = await connection.fetch(
                    "SELECT * FROM messages WHERE chat_id=$1 ORDER BY inserted_at DESC",
                    chat_id,
                )
            return [MessageInDb(**record) for record in reversed(records)]
