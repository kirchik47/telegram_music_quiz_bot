from abc import ABC, abstractmethod


class SpotifyServiceInterface(ABC):
    @abstractmethod
    async def get_preview(self, song_id: str) -> tuple:
        """
        Retrieves the preview URL and the artist's name for a given song ID.

        :param song_id: The Spotify ID of the song
        :return: A tuple containing the preview URL and the song title with artist(s)
        """
        pass

    @abstractmethod
    async def get_song_id(self, url: str) -> str:
        """
        Extracts the song ID from a given Spotify URL.

        :param url: The Spotify URL of the song
        :return: The song ID if found, otherwise None
        """
        pass
