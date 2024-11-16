from pydantic import BaseModel


class CyrisHuman(BaseModel):
    ai_name: str = "Cyris"
    human_name: str = "Human"
    user_id: str = "development_user_id"
