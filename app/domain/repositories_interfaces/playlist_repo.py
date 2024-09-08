from app.domain.entities.playlist import Playlist
from abc import ABC, abstractmethod


class PlaylistRepoInterface(ABC):
    @abstractmethod
    def get(self, playlist: Playlist) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    def save(self, playlist: Playlist) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, playlist: Playlist) -> Playlist:
        raise NotImplementedError
    