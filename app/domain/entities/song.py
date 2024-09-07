from pydantic import BaseModel
from typing import Optional


class Song(BaseModel):
    id: str
    title: Optional[str] = None
    playlist_id: int
    
    def update(self, field, value):
        if hasattr(self, field):
            setattr(self, field, value)
    