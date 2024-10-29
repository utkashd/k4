import logging
import asyncpg  # type: ignore[import-untyped]

from backend_commons import PostgresTableManager
from backend_commons.messages import Message
from rich.logging import RichHandler


from pydantic import BaseModel

from backend.src.backend.user_management import RegisteredUser

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class MessageInDb(BaseModel):
    chat_id: int
    user: RegisteredUser


class MessagesManager(PostgresTableManager):
    def _get_table_name(self) -> str:
        return "messages"

    def _get_pydantic_schema(self) -> type[BaseModel]:
        return MessageInDb
