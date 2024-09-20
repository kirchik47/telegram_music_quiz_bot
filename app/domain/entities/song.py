from pydantic import BaseModel
from typing import Optional


"""
Song Entity:
1. id (str): Unique identifier for the song. Cannot be None.
Other fields can be None because for some functionality we need only id(e.g get method).
2. title (str, Optional): The title of the song.
3. playlist_id (str): Identifier of the playlist this song belongs to.
"""
class Song(BaseModel):
    id: str
    title: Optional[str] = None
    playlist_id: str
    