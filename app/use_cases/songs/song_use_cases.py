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
        song_id = await self.spotify_service.get_song_id(url=url)
        preview, song_title = await self.spotify_service.get_preview(song_id=song_id)
        if preview:
            song = Song(id=song_id, title=song_title, playlist_id=playlist_id)
            await self.s3_repo.save(song, preview)
            await self.sql_repo.save(song)
            await self.redis_repo.save(song)
            return song

    async def delete(self, song: Song) -> None:
        await self.sql_repo.delete(song)
        await self.redis_repo.delete(song)

    async def get(self, song: Song) -> Song:
        # If song is in redis, return it from redis, otherwise from sql
        redis_info = await self.redis_repo.get(song)
        if redis_info:
            return redis_info
        song = await self.sql_repo.get(song)
        await self.redis_repo.save(song)
        return song

    async def read_file(self, song: Song) -> bytes:
        return await self.s3_repo.get(song)