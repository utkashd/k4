from pydantic import BaseModel, Field, RootModel
from uuid import UUID


class Message(BaseModel):
    text: str
    sender_id: str
    chat_id: int = 1


class Messages(RootModel):  # type: ignore[type-arg]
    root: list[Message]


class ClientMessage(Message):
    """
    A message from a client
    """

    client_generated_uuid: UUID


class GptHomeConfirmingReceiptOfClientMessage(BaseModel):
    client_generated_uuid: UUID


class GptHomeMessage(Message):
    """
    A message from GptHome
    """

    sender_id: str = Field(default="gpt_home")


class GptHomeSystemMessage(GptHomeMessage):
    """
    A system message from GptHome (not to be confused with a system message for an LLM)
    """

    sender_id: str = Field(default="gpt_home_system")


class GptHomeMessages(RootModel):  # type: ignore[type-arg]
    root: list[GptHomeSystemMessage | GptHomeMessage]
