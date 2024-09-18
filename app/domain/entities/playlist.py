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
