from pydantic import BaseModel
from typing import Optional


"""
Question Entity:
1. id (str): Unique identifier for the question. Cannot be None.
Other fields can be None because for some functionality we need only id(e.g get method).
2. quiz_id (str, None): Identifier of the quiz this question belongs to.
3. text (str, None): The content or text of the question.
4. options (list[str], None): Options for the question. Contains 4 options as the songs identifiers.
5. correct_answer_index (int, None): The correct answer to the question. Contains index in the list of options.
6. creation_time (int, None): The timestamp (in seconds) when the question was created.
Is needed to calculate the score for the question.
"""
class Question(BaseModel):
    id: str
    quiz_id: Optional[str] = None
    text: Optional[str] = None
    options: Optional[list[str]] = None
    correct_answer_index: Optional[int] = None
    creation_time: Optional[int] = None 
