from pydantic import BaseModel, Field, RootModel


class Message(BaseModel):
    text: str
    sender_id: str


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

    sender_id: str = Field(default="gpt_home")


class GptHomeSystemMessage(GptHomeMessage):
    """
    A system message from GptHome (not to be confused with a system message for an LLM)
    """

    sender_id: str = Field(default="gpt_home_system")


class GptHomeMessages(RootModel):  # type: ignore[type-arg]
    root: list[GptHomeSystemMessage | GptHomeMessage]
