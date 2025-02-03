import datetime

from pydantic import BaseModel, RootModel


class MessageInDb(BaseModel):
    message_id: int
    chat_id: int
    user_id: int | None
    text: str
    inserted_at: datetime.datetime


class Message(BaseModel):
    text: str
    sender_id: int
    chat_id: int


class Messages(RootModel):  # type: ignore[type-arg]
    root: list[Message]
