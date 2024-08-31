from entities.playlist import Playlist
from abc import ABC, abstractmethod


class PlaylistRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> Playlist:
        raise NotImplementedError

    def get_by_name(self, name: str) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    def save(self, fields: dict) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    def delete_by_id(self, user_id: str) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    def update_by_id(self, user_id: str, fields: dict) -> Playlist:
        raise NotImplementedError
    