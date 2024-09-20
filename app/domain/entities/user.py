from pydantic import BaseModel
from typing import Optional


"""
User Entity:
1. id (str): Unique identifier for the user. Cannot be None.
Other fields can be None because for some functionality we need only id(e.g get method).
2. username (str, Optional): The username of the user.
3. playlists (list, Optional): List of playlist instances that the user owns or has created.
"""
class User(BaseModel):
    id: str
    username: Optional[str] = None
    playlists: Optional[list] = None
