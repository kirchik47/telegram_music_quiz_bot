from app.domain.entities.playlist import Playlist
from abc import ABC, abstractmethod


class PlaylistRepoInterface(ABC):
    @abstractmethod
    def get(self, user_id: str) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    def save(self, fields: dict) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, user_id: str) -> Playlist:
        raise NotImplementedError
    