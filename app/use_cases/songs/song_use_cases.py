from app.domain.repositories_interfaces.song_repo import SongRepoInterface
from app.domain.entities.song import Song
from app.domain.services_interfaces.spotify_service import SpotifyServiceInterface


class SongUseCases:
    def __init__(self, sql_repo: SongRepoInterface, redis_repo: SongRepoInterface, 
                 s3_repo: SongRepoInterface, spotify_service: SpotifyServiceInterface):
        self.sql_repo = sql_repo
        self.redis_repo = redis_repo
        self.s3_repo = s3_repo
        self.spotify_service = spotify_service

    async def add(self, url: str, playlist_id: str) -> Song:
        """
        Adds a new song to the playlist by retrieving its metadata and preview from Spotify.

        This method saves the song in S3, SQL, and Redis if the preview exists.

        :param url: The URL of the song on Spotify.
        :param playlist_id: The ID of the playlist to which the song will be added.
        :return: The added Song object if the preview exists; otherwise, None.
        """
        # Retrieve song metadata and preview from Spotify
        song_id = await self.spotify_service.get_song_id(url=url)
        preview, song_title = await self.spotify_service.get_preview(song_id=song_id)

        # If preview exists, save song in S3, SQL, and Redis
        if preview:
            song = Song(id=song_id, title=song_title, playlist_id=playlist_id)
            await self.s3_repo.save(song, preview)
            await self.sql_repo.save(song)
            await self.redis_repo.save(song)
            return song

    async def delete(self, song_id: str, playlist_id: str) -> None:
        """
        Deletes a song from the playlist.

        This method removes the song from both SQL and Redis repositories.

        :param song_id: The ID of the song to be deleted.
        :param playlist_id: The ID of the playlist from which the song will be removed.
        """
        # Remove song from both SQL and Redis
        song = Song(id=song_id, playlist_id=playlist_id)
        await self.sql_repo.delete(song)
        await self.redis_repo.delete(song)

    async def get(self, song_id: str, playlist_id: str) -> Song:
        """
        Retrieves a song from the playlist.

        This method attempts to fetch the song from Redis first. If it is not available, it retrieves
        it from SQL and updates the Redis cache.

        :param song_id: The ID of the song to be retrieved.
        :param playlist_id: The ID of the playlist to which the song belongs.
        :return: The retrieved Song object.
        """
        # Try to get the song from Redis; if not available, get it from SQL and update Redis
        song = Song(id=song_id, playlist_id=playlist_id)
        redis_info = await self.redis_repo.get(song)
        if redis_info:
            return redis_info
        song = await self.sql_repo.get(song)
        await self.redis_repo.save(song)
        return song

    async def read_file(self, song_title: str) -> bytes:
        """
        Retrieves the preview file of a song from S3.

        :param song_id: The ID of the song to be retrieved.
        :param playlist_id: The ID of the playlist to which the song belongs.
        :param song_title: The title of the song.
        :return: The preview file in bytes.
        """
        # Retrieve song preview file from S3
        song = Song(title=song_title)
        return await self.s3_repo.get(song)
