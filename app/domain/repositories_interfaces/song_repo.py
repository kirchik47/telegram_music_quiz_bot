from app.domain.entities.song import Song
from abc import ABC, abstractmethod


class SongRepoInterface(ABC):
    @abstractmethod
    def get(self, song: Song) -> Song:
        raise NotImplementedError
    
    @abstractmethod
    def save(self, song: Song) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, song: Song) -> None:
        raise NotImplementedError
    
    