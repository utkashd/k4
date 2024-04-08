from pydantic import BaseModel, Field, RootModel


class Message(BaseModel):
    text: str
    senderId: str


class Messages(RootModel):  # type: ignore[type-arg]
    root: list[Message]


class ClientMessage(Message):
    """
    A message from a client
    """

    pass


class GptHomeMessage(Message):
    """
    A message from GptHome
    """

    senderId: str = Field(default="gpt_home")


class GptHomeSystemMessage(GptHomeMessage):
    """
    A system message from GptHome (not to be confused with a system message for an LLM)
    """

    senderId: str = Field(default="system")


class GptHomeMessages(RootModel):  # type: ignore[type-arg]
    root: list[GptHomeSystemMessage | GptHomeMessage]
