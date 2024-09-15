from pydantic import BaseModel
from typing import Optional
from app.domain.entities.song import Song


class Playlist(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: Optional[str] = None
    is_public: Optional[bool] = None
    description: Optional[str] = None
    songs: Optional[list[Song]] = None


    def update(self, field, value):
        if hasattr(self, field):
            setattr(self, field, value)
    
