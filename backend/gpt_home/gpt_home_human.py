from pydantic import BaseModel


class GptHomeHuman(BaseModel):
    ai_name: str = "GptHome"
    human_name: str = "Human"
    user_id: str = "development_user_id"
