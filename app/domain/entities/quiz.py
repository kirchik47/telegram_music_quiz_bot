from pydantic import BaseModel
from typing import Optional
from app.domain.entities.question import Question


class Quiz(BaseModel):
    id: str
    user_id: Optional[str] = None
    songs_left: Optional[list[str]] = None
    points: Optional[int] = None
    quiz_type: Optional[str] = None
    questions_left: Optional[int] = None
    max_points: Optional[int] = None
    inviters_info: Optional[list] = None
    questions: Optional[list[Question]] = None
