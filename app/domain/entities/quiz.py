from pydantic import BaseModel
from typing import Optional
from app.domain.entities.question import Question


"""
Quiz Entity:
1. id (str): Unique identifier for the quiz. Cannot be None.
Other fields can be None because for some functionality we need only id(e.g get method).
2. user_id (str, None): Identifier of the user who created the quiz.
3. songs_left (list[str], None): List of song identifiers remaining in the quiz.
4. points (int, None): The current points scored by the user in the quiz.
5. quiz_type (str, None): Type of the quiz (e.g. guess the song by preview quiz, guess the song by fact).
6. questions_left (int, None): The number of questions remaining in the quiz.
7. max_points (int, None): The maximum possible points for the quiz.
8. inviter_info (list, None): Information about user who have invited the other one to take a quiz.
9. questions (list[Question], None): List of question instances associated with the quiz.
"""
class Quiz(BaseModel):
    id: str
    user_id: Optional[str] = None
    songs_left: Optional[list[str]] = None
    points: Optional[int] = None
    quiz_type: Optional[str] = None
    questions_left: Optional[int] = None
    max_points: Optional[int] = None
    inviter_info: Optional[list] = None
    questions: Optional[list[Question]] = None
