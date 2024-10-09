from pydantic import BaseModel
from typing import Optional
from app.domain.entities.question import Question


"""
Quiz Entity:
1. id (str): Unique identifier for the quiz. Cannot be None.
Other fields can be None because for some functionality we need only id(e.g get method).
2. user_id (str, None): Identifier of the user who created the quiz.
3. points (int, None): The current points scored by the user in the quiz.
4. quiz_type (bool, None): Type of the quiz (e.g. guess the song by preview quiz, guess the song by fact).
Currently bool, in future can be changed to int if more types are added than 2.
5. max_points_per_question (int, None): The maximum possible points for the question.
6. questions (list[Question], None): List of question instances associated with the quiz.
"""
class Quiz(BaseModel):
    id: str
    user_id: Optional[str] = None
    points: Optional[int] = None
    quiz_type: Optional[str] = None
    max_points_per_question: Optional[int] = None
    questions: Optional[list[Question]] = None
