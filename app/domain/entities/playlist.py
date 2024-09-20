from pydantic import BaseModel
from typing import Optional
from app.domain.entities.song import Song

"""
Playlist Entity:
1. id (int): Unique identifier for the playlist. Cannot be None. 
Other fields can be None because for some functionality we need only id(e.g get method).
2. name (str): Name of the playlist.
3. description (str): Description of the playlist.
4. songs (list): List of songs in the playlist. Contains list os songs instances with metadata.
"""

class Playlist(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: Optional[str] = None
    is_public: Optional[bool] = None
    description: Optional[str] = None
    songs: Optional[list[Song]] = None
