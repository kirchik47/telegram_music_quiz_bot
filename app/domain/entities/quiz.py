from pydantic import BaseModel
from typing import Optional


class Quiz(BaseModel):
    id: str
    user_id: Optional[str] = None
    songs_left: Optional[list[str]] = None
    points: Optional[int] = None
    quiz_type: Optional[str] = None
    questions_left: Optional[int] = None
    max_points: Optional[int] = None
    inviters_info: Optional[list] = None
    
    def update(self, field, value):
        if hasattr(self, field):
            setattr(self, field, value)
