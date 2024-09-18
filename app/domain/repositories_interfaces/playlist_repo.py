from app.domain.entities.playlist import Playlist
from abc import ABC, abstractmethod


class PlaylistRepoInterface(ABC):
    @abstractmethod
    async def get(self, playlist: Playlist) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    async def save(self, playlist: Playlist) -> Playlist:
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, playlist: Playlist) -> Playlist:
        raise NotImplementedError
    