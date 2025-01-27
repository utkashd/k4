import datetime
from uuid import UUID

from pydantic import BaseModel, Field, RootModel


class MessageInDb(BaseModel):
    message_id: int
    chat_id: int
    user_id: int | None
    text: str
    inserted_at: datetime.datetime


class Message(BaseModel):
    text: str
    sender_id: int
    chat_id: int = 1


class Messages(RootModel):  # type: ignore[type-arg]
    root: list[Message]


class ClientMessage(Message):
    """
    A message from a client
    """

    client_generated_message_uuid: UUID


class CyrisConfirmingReceiptOfClientMessage(BaseModel):
    client_generated_message_uuid: UUID


class CyrisMessage(Message):
    """
    A message from Cyris
    """

    sender_id: int = Field(default=0)


class CyrisSystemMessage(CyrisMessage):
    """
    A system message from Cyris (not to be confused with a system message for an LLM)
    """

    sender_id: int = Field(default=-1)


class CyrisMessages(RootModel):  # type: ignore[type-arg]
    root: list[CyrisSystemMessage | CyrisMessage]
