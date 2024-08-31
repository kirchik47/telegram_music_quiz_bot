from entities.song import Song
from abc import ABC, abstractmethod


class SongRepository(ABC):
    @abstractmethod
    def get_by_song_id_playlist_id(self, song_id: str, playlist_id: int) -> Song:
        raise NotImplementedError
    
    @abstractmethod
    def save(self, fields: dict) -> Song:
        raise NotImplementedError
    
    @abstractmethod
    def delete_by_song_id_playlist_id(self, song_id: str, playlist_id: int) -> Song:
        raise NotImplementedError
    
    