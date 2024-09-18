from pydantic import BaseModel
from typing import Optional


class Song(BaseModel):
    id: str
    title: Optional[str] = None
    playlist_id: str
    