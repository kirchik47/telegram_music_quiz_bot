from abc import ABC, abstractmethod

class GeniusServiceInterface(ABC):
    @abstractmethod
    async def search_song(self, song_name: str) -> str:
        """
        Searches for a song on Genius by name and retrieves the API path for the song.

        :param song_name: The name of the song to search
        :return: API path for the first result
        """
        pass

    @abstractmethod
    async def get_song_info(self, api_path: str) -> dict:
        """
        Retrieves song information such as description and lyrics URL using the provided API path.

        :param api_path: The API path of the song
        :return: Dictionary containing 'description' and 'lyrics_url'
        """
        pass

    @abstractmethod
    async def get_lyrics(self, lyrics_url: str) -> str:
        """
        Scrapes the lyrics of the song from the Genius lyrics page.

        :param lyrics_url: The URL to the Genius lyrics page
        :return: The song lyrics as a string
        """
        pass

    @abstractmethod
    async def retrieve_info(self, song_name: str) -> dict:
        """
        Retrieves full song information including both the description and lyrics by combining the search,
        song info retrieval, and lyrics scraping processes.

        :param song_name: The name of the song to retrieve information for
        :return: Dictionary with 'description' and 'lyrics' keys
        """
        pass
