import logging
import datetime
from typing import Iterable

from backend_commons import PostgresTableManager
from rich.logging import RichHandler


from pydantic import BaseModel, Field


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")


class ChatInDb(BaseModel):
    chat_id: int
    user_id: int
    title: str = Field(max_length=32)
    last_message_timestamp: datetime.datetime
    is_archived: bool


class MessageInDb(BaseModel):
    message_id: int
    chat_id: int
    user_id: int | None
    text: str
    inserted_at: datetime.datetime


class ChatPreview(BaseModel):
    chat_in_db: ChatInDb
    message_in_db: MessageInDb


class MessagesManager(PostgresTableManager):
    @property
    def create_table_queries(self) -> list[str]:
        # If you're changing the tables, you'll need to drop the existing table
        # on your local machine first. Something like:
        # > `$ docker exec -it cyris-dev-postgres bash`
        # > > `$ psql -U postgres`
        # > > > `$ \c postgres` # connect to the DB named "postgres"
        # > > > `$ \d` # show the tables
        # > > > `$ drop table messages;`
        # `exit` a couple times to return to your terminal

        # Creating foreign keys syntax:
        # https://stackoverflow.com/questions/28558920/postgresql-foreign-key-syntax
        # In the messages table, a null value for user_id indicates the message was sent
        # by cyris (and not by a user)
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

    async def create_new_chat(self, user_id: int, title: str):
        if len(title) > 32:
            title = title[:29] + "..."
        async with self.get_transaction_connection() as connection:
            new_chat = await connection.fetchrow(
                "INSERT INTO chats (user_id, title, is_archived) VALUES ($1, $2, $3) RETURNING *",
                user_id,
                title,
                False,
            )
            return ChatInDb(**new_chat)

    async def save_message_to_db(
        self, chat_id: int, user_id: int | None, text: str
    ) -> MessageInDb:
        """
        Parameters
        ----------
        user_id : int | None
            `None` iff the message is from cyris
        """
        async with self.get_transaction_connection() as connection:
            new_message = await connection.fetchrow(
                "INSERT INTO messages (chat_id, user_id, text) VALUES ($1, $2, $3) RETURNING *",
                chat_id,
                user_id,
                text,
            )
            new_message_in_db = MessageInDb(**new_message)
            await connection.execute(
                "UPDATE chats SET last_message_timestamp=$1 WHERE chat_id=$2",
                new_message_in_db.inserted_at,
                new_message_in_db.chat_id,
            )
            return new_message_in_db

    async def save_cyris_message_to_db(self, chat_id: int, text: str) -> MessageInDb:
        return await self.save_message_to_db(chat_id=chat_id, user_id=None, text=text)

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
                chat_previews.append(
                    ChatPreview(
                        chat_in_db=ChatInDb(**chat),
                        message_in_db=MessageInDb(**latest_message),
                    )
                )
            return chat_previews

    async def get_messages_of_chat(self, chat_id: int) -> Iterable[MessageInDb]:
        # TODO reverse-paginate
        async with self.get_connection() as connection:
            records = await connection.fetch(
                "SELECT * FROM messages WHERE chat_id=$1", chat_id
            )
            return [MessageInDb(**record) for record in records]
