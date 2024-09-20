from pydantic import BaseModel
from typing import Optional


class Question(BaseModel):
    id: str
    quiz_id: str
    text: str
    correct_answer: str
    creation_time: int 
