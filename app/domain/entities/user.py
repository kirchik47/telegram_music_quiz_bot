from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    id: str
    username: Optional[str] = None
    playlists: Optional[list] = None

    def update(self, field: str, value):
        if hasattr(self, field):
            setattr(self, field, value)
