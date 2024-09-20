from abc import ABC, abstractmethod


class SpotifyServiceInterface(ABC):
    async def get_preview(self, song_id: str):
        raise NotImplementedError

    async def get_song_id(self, url: str):
        raise NotImplementedError
    