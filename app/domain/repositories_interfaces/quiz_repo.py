from entities.song import Song
from abc import ABC, abstractmethod


class QuizRepoInterface(ABC):
    @abstractmethod
    def get(self, song_id: str, playlist_id: int) -> Song:
        raise NotImplementedError
    
    @abstractmethod
    def save(self, fields: dict) -> Song:
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, song_id: str, playlist_id: int) -> Song:
        raise NotImplementedError
    
    