from app.domain.entities.song import Song
from abc import ABC, abstractmethod


class SongRepoInterface(ABC):
    @abstractmethod
    async def get(self, song: Song) -> Song:
        raise NotImplementedError
    
    @abstractmethod
    async def save(self, song: Song) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, song: Song) -> None:
        raise NotImplementedError
    
    